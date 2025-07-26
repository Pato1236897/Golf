from fastapi import FastAPI, APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import json
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
import uuid
from datetime import datetime
from enum import Enum

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.user_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, match_id: str, user_id: str):
        await websocket.accept()
        if match_id not in self.active_connections:
            self.active_connections[match_id] = []
        self.active_connections[match_id].append(websocket)
        self.user_connections[user_id] = websocket

    def disconnect(self, websocket: WebSocket, match_id: str, user_id: str):
        if match_id in self.active_connections:
            self.active_connections[match_id].remove(websocket)
        if user_id in self.user_connections:
            del self.user_connections[user_id]

    async def send_to_team(self, match_id: str, team_id: str, message: dict):
        """Send message only to team members"""
        if match_id in self.active_connections:
            # Get team members for this match
            match = await db.matches.find_one({"id": match_id})
            if match:
                team_members = []
                for team in match.get("teams", []):
                    if team["id"] == team_id:
                        team_members = [player["id"] for player in team["players"]]
                        break
                
                # Send to team members only
                for connection in self.active_connections[match_id]:
                    try:
                        # Check if this connection belongs to a team member
                        for user_id, websocket in self.user_connections.items():
                            if websocket == connection and user_id in team_members:
                                await connection.send_text(json.dumps(message))
                                break
                    except:
                        pass

    async def send_to_match(self, match_id: str, message: dict):
        """Send message to all participants in match"""
        if match_id in self.active_connections:
            for connection in self.active_connections[match_id]:
                try:
                    await connection.send_text(json.dumps(message))
                except:
                    pass

manager = ConnectionManager()

class MatchType(str, Enum):
    STROKE_PLAY = "stroke_play"
    SCRAMBLE = "scramble"

class MatchStatus(str, Enum):
    SETUP = "setup"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

# Data Models
class Player(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    email: Optional[str] = None
    handicap: Optional[int] = 0

class PlayerCreate(BaseModel):
    name: str
    email: Optional[str] = None
    handicap: Optional[int] = 0

class Team(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    color: str = "#3B82F6"  # Default blue
    players: List[Player] = []
    captain_id: Optional[str] = None

class TeamCreate(BaseModel):
    name: str
    color: Optional[str] = "#3B82F6"
    players: List[PlayerCreate] = []

class Score(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    match_id: str
    player_id: str
    hole: int
    strokes: int
    putts: Optional[int] = 0
    penalties: Optional[int] = 0
    best_shot: Optional[bool] = False
    best_shot_description: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ScoreInput(BaseModel):
    player_id: str
    hole: int
    strokes: int
    putts: Optional[int] = 0
    penalties: Optional[int] = 0
    best_shot: Optional[bool] = False
    best_shot_description: Optional[str] = None

class Match(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    match_type: MatchType
    holes: int = 18
    teams: List[Team] = []
    status: MatchStatus = MatchStatus.SETUP
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    creator_id: str

class MatchCreate(BaseModel):
    name: str
    match_type: MatchType = MatchType.STROKE_PLAY
    holes: int = 18
    teams: List[TeamCreate] = []
    creator_id: str

class BestShot(BaseModel):
    hole: int
    player_id: str
    player_name: str
    team_id: str
    description: str
    votes: int = 0

class MatchStats(BaseModel):
    best_shots: List[BestShot] = []
    best_players: Dict[str, Dict[str, Any]] = {}  # team_id -> player stats

# API Endpoints
@api_router.get("/")
async def root():
    return {"message": "Golf Scorekeeping API"}

@api_router.post("/matches", response_model=Match)
async def create_match(match_data: MatchCreate):
    """Create a new golf match with teams"""
    # Convert teams
    teams = []
    for team_data in match_data.teams:
        players = [Player(**player.dict()) for player in team_data.players]
        team = Team(
            name=team_data.name,
            color=team_data.color,
            players=players,
            captain_id=players[0].id if players else None
        )
        teams.append(team)
    
    match = Match(
        name=match_data.name,
        match_type=match_data.match_type,
        holes=match_data.holes,
        teams=teams,
        creator_id=match_data.creator_id
    )
    
    await db.matches.insert_one(match.dict())
    return match

@api_router.get("/matches", response_model=List[Match])
async def get_matches():
    """Get all matches"""
    matches = await db.matches.find().to_list(100)
    return [Match(**match) for match in matches]

@api_router.get("/matches/{match_id}", response_model=Match)
async def get_match(match_id: str):
    """Get a specific match"""
    match = await db.matches.find_one({"id": match_id})
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    return Match(**match)

@api_router.post("/matches/{match_id}/start")
async def start_match(match_id: str):
    """Start a match"""
    result = await db.matches.update_one(
        {"id": match_id},
        {
            "$set": {
                "status": MatchStatus.IN_PROGRESS,
                "started_at": datetime.utcnow()
            }
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Match not found")
    
    # Notify all participants
    await manager.send_to_match(match_id, {
        "type": "match_started",
        "match_id": match_id,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    return {"message": "Match started"}

@api_router.post("/matches/{match_id}/scores")
async def submit_score(match_id: str, score_data: ScoreInput):
    """Submit a score for a hole"""
    # Check if match exists
    match = await db.matches.find_one({"id": match_id})
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    if match["status"] != MatchStatus.IN_PROGRESS:
        raise HTTPException(status_code=400, detail="Match is not in progress")
    
    # Create score record
    score = Score(
        match_id=match_id,
        **score_data.dict()
    )
    
    # Save score
    await db.scores.insert_one(score.dict())
    
    # Find player's team
    player_team_id = None
    player_name = "Unknown"
    for team in match["teams"]:
        for player in team["players"]:
            if player["id"] == score_data.player_id:
                player_team_id = team["id"]
                player_name = player["name"]
                break
        if player_team_id:
            break
    
    # Send real-time update to team members only
    if player_team_id:
        await manager.send_to_team(match_id, player_team_id, {
            "type": "score_update",
            "score": {
                "player_id": score_data.player_id,
                "player_name": player_name,
                "hole": score_data.hole,
                "strokes": score_data.strokes,
                "putts": score_data.putts,
                "penalties": score_data.penalties,
                "best_shot": score_data.best_shot,
                "best_shot_description": score_data.best_shot_description
            }
        })
    
    return {"message": "Score submitted successfully"}

@api_router.get("/matches/{match_id}/scores")
async def get_match_scores(match_id: str, team_id: Optional[str] = None):
    """Get scores for a match with privacy controls"""
    match = await db.matches.find_one({"id": match_id})
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    scores = await db.scores.find({"match_id": match_id}).to_list(1000)
    
    # Remove MongoDB _id field to avoid serialization issues
    for score in scores:
        if "_id" in score:
            del score["_id"]
    
    # If match is completed, show all scores
    if match["status"] == MatchStatus.COMPLETED:
        return scores
    
    # If match is in progress, only show team member scores
    if team_id and match["status"] == MatchStatus.IN_PROGRESS:
        # Get team member IDs
        team_player_ids = []
        for team in match["teams"]:
            if team["id"] == team_id:
                team_player_ids = [player["id"] for player in team["players"]]
                break
        
        # Filter scores to only include team members
        filtered_scores = [score for score in scores if score["player_id"] in team_player_ids]
        return filtered_scores
    
    return []

@api_router.get("/matches/{match_id}/leaderboard")
async def get_leaderboard(match_id: str, team_id: Optional[str] = None):
    """Get leaderboard with privacy controls"""
    match = await db.matches.find_one({"id": match_id})
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    scores = await db.scores.find({"match_id": match_id}).to_list(1000)
    
    # Calculate leaderboard
    player_totals = {}
    
    for score in scores:
        player_id = score["player_id"]
        if player_id not in player_totals:
            player_totals[player_id] = {
                "total_strokes": 0,
                "holes_played": 0,
                "best_shots": 0
            }
        
        player_totals[player_id]["total_strokes"] += score["strokes"]
        player_totals[player_id]["holes_played"] += 1
        if score.get("best_shot"):
            player_totals[player_id]["best_shots"] += 1
    
    # Add player names and team info
    leaderboard = []
    for team in match["teams"]:
        for player in team["players"]:
            if player["id"] in player_totals:
                player_stats = player_totals[player["id"]]
                
                # Privacy logic
                if match["status"] == MatchStatus.COMPLETED or (team_id and team["id"] == team_id):
                    # Show actual scores
                    leaderboard.append({
                        "player_id": player["id"],
                        "player_name": player["name"],
                        "team_id": team["id"],
                        "team_name": team["name"],
                        "team_color": team["color"],
                        "total_strokes": player_stats["total_strokes"],
                        "holes_played": player_stats["holes_played"],
                        "best_shots": player_stats["best_shots"]
                    })
                else:
                    # Hide opponent scores
                    leaderboard.append({
                        "player_id": player["id"],
                        "player_name": player["name"],
                        "team_id": team["id"],
                        "team_name": team["name"],
                        "team_color": team["color"],
                        "total_strokes": "???",
                        "holes_played": "???",
                        "best_shots": "???"
                    })
    
    # Sort by total strokes (only for completed matches or team view)
    if match["status"] == MatchStatus.COMPLETED or team_id:
        leaderboard.sort(key=lambda x: x["total_strokes"] if isinstance(x["total_strokes"], int) else 999)
    
    return leaderboard

@api_router.post("/matches/{match_id}/complete")
async def complete_match(match_id: str):
    """Complete a match and calculate final awards"""
    match = await db.matches.find_one({"id": match_id})
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    # Mark match as completed
    await db.matches.update_one(
        {"id": match_id},
        {
            "$set": {
                "status": MatchStatus.COMPLETED,
                "completed_at": datetime.utcnow()
            }
        }
    )
    
    # Calculate awards
    scores = await db.scores.find({"match_id": match_id}).to_list(1000)
    
    # Best shots by hole
    best_shots = []
    holes_processed = set()
    
    for score in scores:
        if score.get("best_shot") and score["hole"] not in holes_processed:
            # Find player and team info
            player_name = "Unknown"
            team_id = None
            for team in match["teams"]:
                for player in team["players"]:
                    if player["id"] == score["player_id"]:
                        player_name = player["name"]
                        team_id = team["id"]
                        break
                if team_id:
                    break
            
            best_shots.append({
                "hole": score["hole"],
                "player_id": score["player_id"],
                "player_name": player_name,
                "team_id": team_id,
                "description": score.get("best_shot_description", "Great shot!")
            })
            holes_processed.add(score["hole"])
    
    # Best players by team
    best_players = {}
    team_stats = {}
    
    # Calculate team statistics
    for team in match["teams"]:
        team_id = team["id"]
        team_stats[team_id] = {}
        
        for player in team["players"]:
            player_id = player["id"]
            player_scores = [s for s in scores if s["player_id"] == player_id]
            
            if player_scores:
                total_strokes = sum(s["strokes"] for s in player_scores)
                best_shots_count = sum(1 for s in player_scores if s.get("best_shot"))
                holes_played = len(player_scores)
                
                team_stats[team_id][player_id] = {
                    "name": player["name"],
                    "total_strokes": total_strokes,
                    "best_shots": best_shots_count,
                    "holes_played": holes_played,
                    "average": total_strokes / holes_played if holes_played > 0 else 0
                }
    
    # Find best player per team (lowest score)
    for team_id, players in team_stats.items():
        if players:
            best_player = min(players.items(), key=lambda x: x[1]["total_strokes"])
            best_players[team_id] = {
                "player_id": best_player[0],
                "player_name": best_player[1]["name"],
                "total_strokes": best_player[1]["total_strokes"],
                "best_shots": best_player[1]["best_shots"]
            }
    
    # Notify all participants that match is complete
    await manager.send_to_match(match_id, {
        "type": "match_completed",
        "match_id": match_id,
        "best_shots": best_shots,
        "best_players": best_players
    })
    
    return {
        "message": "Match completed",
        "best_shots": best_shots,
        "best_players": best_players
    }

# WebSocket endpoint
@app.websocket("/ws/{match_id}/{user_id}")
async def websocket_endpoint(websocket: WebSocket, match_id: str, user_id: str):
    await manager.connect(websocket, match_id, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming messages if needed
            pass
    except WebSocketDisconnect:
        manager.disconnect(websocket, match_id, user_id)

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()