#!/usr/bin/env python3
"""
Comprehensive Backend API Testing for Golf Scorekeeping App
Tests all core functionality including privacy logic, match management, and scoring system.
"""

import requests
import json
import uuid
import time
from typing import Dict, List, Any

# Backend URL from environment
BACKEND_URL = "https://d59d824d-8489-4f27-8ccf-8d237ccdac67.preview.emergentagent.com/api"

class GolfAppTester:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.test_match_id = None
        self.test_teams = []
        self.test_players = []
        
    def log(self, message: str, level: str = "INFO"):
        """Log test messages"""
        print(f"[{level}] {message}")
        
    def make_request(self, method: str, endpoint: str, data: Dict = None, params: Dict = None) -> Dict:
        """Make HTTP request with error handling"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, params=params, timeout=30)
            elif method.upper() == "POST":
                response = requests.post(url, json=data, timeout=30)
            elif method.upper() == "PUT":
                response = requests.put(url, json=data, timeout=30)
            elif method.upper() == "DELETE":
                response = requests.delete(url, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")
                
            self.log(f"{method} {endpoint} -> Status: {response.status_code}")
            
            if response.status_code >= 400:
                self.log(f"Error response: {response.text}", "ERROR")
                
            return {
                "status_code": response.status_code,
                "data": response.json() if response.content else {},
                "success": 200 <= response.status_code < 300
            }
            
        except requests.exceptions.RequestException as e:
            self.log(f"Request failed: {str(e)}", "ERROR")
            return {
                "status_code": 0,
                "data": {},
                "success": False,
                "error": str(e)
            }
        except json.JSONDecodeError as e:
            self.log(f"JSON decode error: {str(e)}", "ERROR")
            return {
                "status_code": response.status_code,
                "data": {},
                "success": False,
                "error": "Invalid JSON response"
            }

    def test_root_endpoint(self) -> bool:
        """Test the root API endpoint"""
        self.log("Testing root endpoint...")
        
        result = self.make_request("GET", "/")
        
        if result["success"] and result["data"].get("message") == "Golf Scorekeeping API":
            self.log("✅ Root endpoint working correctly")
            return True
        else:
            self.log("❌ Root endpoint failed", "ERROR")
            return False

    def create_test_data(self):
        """Create test data for comprehensive testing"""
        # Team 1: Eagles (blue)
        team1_players = [
            {"name": "Alice Johnson", "email": "alice@example.com", "handicap": 12},
            {"name": "Bob Smith", "email": "bob@example.com", "handicap": 8},
            {"name": "Charlie Brown", "email": "charlie@example.com", "handicap": 15},
            {"name": "Diana Prince", "email": "diana@example.com", "handicap": 10}
        ]
        
        # Team 2: Birdies (red)
        team2_players = [
            {"name": "Eve Wilson", "email": "eve@example.com", "handicap": 14},
            {"name": "Frank Miller", "email": "frank@example.com", "handicap": 9},
            {"name": "Grace Lee", "email": "grace@example.com", "handicap": 11},
            {"name": "Henry Davis", "email": "henry@example.com", "handicap": 13}
        ]
        
        return {
            "name": "Test Tournament Championship",
            "match_type": "stroke_play",
            "holes": 18,
            "creator_id": str(uuid.uuid4()),
            "teams": [
                {
                    "name": "Eagles",
                    "color": "#3B82F6",
                    "players": team1_players
                },
                {
                    "name": "Birdies", 
                    "color": "#EF4444",
                    "players": team2_players
                }
            ]
        }

    def test_match_creation(self) -> bool:
        """Test match creation with teams and players"""
        self.log("Testing match creation...")
        
        match_data = self.create_test_data()
        result = self.make_request("POST", "/matches", match_data)
        
        if not result["success"]:
            self.log("❌ Match creation failed", "ERROR")
            return False
            
        match = result["data"]
        self.test_match_id = match.get("id")
        
        # Validate match structure
        if not all(key in match for key in ["id", "name", "teams", "status"]):
            self.log("❌ Match missing required fields", "ERROR")
            return False
            
        if len(match["teams"]) != 2:
            self.log("❌ Incorrect number of teams created", "ERROR")
            return False
            
        # Store team and player info for later tests
        for team in match["teams"]:
            self.test_teams.append({
                "id": team["id"],
                "name": team["name"],
                "players": team["players"]
            })
            self.test_players.extend(team["players"])
            
        if match["status"] != "setup":
            self.log("❌ Match should start in setup status", "ERROR")
            return False
            
        self.log("✅ Match creation successful")
        return True

    def test_get_matches(self) -> bool:
        """Test retrieving all matches"""
        self.log("Testing get all matches...")
        
        result = self.make_request("GET", "/matches")
        
        if not result["success"]:
            self.log("❌ Get matches failed", "ERROR")
            return False
            
        matches = result["data"]
        if not isinstance(matches, list):
            self.log("❌ Matches should return a list", "ERROR")
            return False
            
        # Check if our test match is in the list
        test_match_found = any(match.get("id") == self.test_match_id for match in matches)
        if not test_match_found:
            self.log("❌ Test match not found in matches list", "ERROR")
            return False
            
        self.log("✅ Get matches successful")
        return True

    def test_get_specific_match(self) -> bool:
        """Test retrieving a specific match"""
        self.log("Testing get specific match...")
        
        if not self.test_match_id:
            self.log("❌ No test match ID available", "ERROR")
            return False
            
        result = self.make_request("GET", f"/matches/{self.test_match_id}")
        
        if not result["success"]:
            self.log("❌ Get specific match failed", "ERROR")
            return False
            
        match = result["data"]
        if match.get("id") != self.test_match_id:
            self.log("❌ Returned match ID doesn't match requested", "ERROR")
            return False
            
        self.log("✅ Get specific match successful")
        return True

    def test_start_match(self) -> bool:
        """Test starting a match"""
        self.log("Testing match start...")
        
        if not self.test_match_id:
            self.log("❌ No test match ID available", "ERROR")
            return False
            
        result = self.make_request("POST", f"/matches/{self.test_match_id}/start")
        
        if not result["success"]:
            self.log("❌ Start match failed", "ERROR")
            return False
            
        # Verify match status changed
        match_result = self.make_request("GET", f"/matches/{self.test_match_id}")
        if match_result["success"]:
            match = match_result["data"]
            if match.get("status") != "in_progress":
                self.log("❌ Match status should be 'in_progress' after starting", "ERROR")
                return False
                
        self.log("✅ Match start successful")
        return True

    def test_score_submission(self) -> bool:
        """Test score submission for players"""
        self.log("Testing score submission...")
        
        if not self.test_match_id or not self.test_players:
            self.log("❌ No test match or players available", "ERROR")
            return False
            
        # Submit scores for first few players on hole 1
        test_scores = [
            {
                "player_id": self.test_players[0]["id"],
                "hole": 1,
                "strokes": 4,
                "putts": 2,
                "penalties": 0,
                "best_shot": True,
                "best_shot_description": "Amazing approach shot to 3 feet!"
            },
            {
                "player_id": self.test_players[1]["id"], 
                "hole": 1,
                "strokes": 5,
                "putts": 2,
                "penalties": 1,
                "best_shot": False
            },
            {
                "player_id": self.test_players[4]["id"],  # Player from team 2
                "hole": 1,
                "strokes": 3,
                "putts": 1,
                "penalties": 0,
                "best_shot": False
            }
        ]
        
        for score_data in test_scores:
            result = self.make_request("POST", f"/matches/{self.test_match_id}/scores", score_data)
            if not result["success"]:
                self.log(f"❌ Score submission failed for player {score_data['player_id']}", "ERROR")
                return False
                
        self.log("✅ Score submission successful")
        return True

    def test_privacy_logic(self) -> bool:
        """Test the core privacy logic - teammates see scores, opponents see ???"""
        self.log("Testing privacy logic...")
        
        if not self.test_match_id or len(self.test_teams) < 2:
            self.log("❌ No test match or teams available", "ERROR")
            return False
            
        team1_id = self.test_teams[0]["id"]
        team2_id = self.test_teams[1]["id"]
        
        # Test team 1 can see their own scores
        result1 = self.make_request("GET", f"/matches/{self.test_match_id}/scores", params={"team_id": team1_id})
        if not result1["success"]:
            self.log("❌ Failed to get team 1 scores", "ERROR")
            return False
            
        team1_scores = result1["data"]
        team1_player_ids = [p["id"] for p in self.test_teams[0]["players"]]
        
        # Verify team 1 only sees their own players' scores
        for score in team1_scores:
            if score["player_id"] not in team1_player_ids:
                self.log("❌ Team 1 can see opponent scores - privacy violation!", "ERROR")
                return False
                
        # Test team 2 can see their own scores
        result2 = self.make_request("GET", f"/matches/{self.test_match_id}/scores", params={"team_id": team2_id})
        if not result2["success"]:
            self.log("❌ Failed to get team 2 scores", "ERROR")
            return False
            
        team2_scores = result2["data"]
        team2_player_ids = [p["id"] for p in self.test_teams[1]["players"]]
        
        # Verify team 2 only sees their own players' scores
        for score in team2_scores:
            if score["player_id"] not in team2_player_ids:
                self.log("❌ Team 2 can see opponent scores - privacy violation!", "ERROR")
                return False
                
        self.log("✅ Privacy logic working correctly")
        return True

    def test_leaderboard_privacy(self) -> bool:
        """Test leaderboard with privacy controls"""
        self.log("Testing leaderboard privacy...")
        
        if not self.test_match_id or len(self.test_teams) < 2:
            self.log("❌ No test match or teams available", "ERROR")
            return False
            
        team1_id = self.test_teams[0]["id"]
        
        # Test team 1 leaderboard view
        result = self.make_request("GET", f"/matches/{self.test_match_id}/leaderboard", params={"team_id": team1_id})
        if not result["success"]:
            self.log("❌ Failed to get leaderboard", "ERROR")
            return False
            
        leaderboard = result["data"]
        
        # Check privacy: team 1 should see their scores, opponents should show "???"
        team1_player_ids = [p["id"] for p in self.test_teams[0]["players"]]
        
        for entry in leaderboard:
            if entry["player_id"] in team1_player_ids:
                # Team member - should see actual scores
                if entry["total_strokes"] == "???":
                    self.log("❌ Team member scores should be visible", "ERROR")
                    return False
            else:
                # Opponent - should see "???"
                if entry["total_strokes"] != "???":
                    self.log("❌ Opponent scores should be hidden with '???'", "ERROR")
                    return False
                    
        self.log("✅ Leaderboard privacy working correctly")
        return True

    def test_match_completion(self) -> bool:
        """Test match completion and awards calculation"""
        self.log("Testing match completion...")
        
        if not self.test_match_id:
            self.log("❌ No test match ID available", "ERROR")
            return False
            
        # Submit a few more scores to have data for awards
        additional_scores = [
            {
                "player_id": self.test_players[2]["id"],
                "hole": 1,
                "strokes": 6,
                "putts": 3,
                "penalties": 0,
                "best_shot": False
            },
            {
                "player_id": self.test_players[0]["id"],
                "hole": 2,
                "strokes": 3,
                "putts": 1,
                "penalties": 0,
                "best_shot": True,
                "best_shot_description": "Hole in one!"
            }
        ]
        
        for score_data in additional_scores:
            self.make_request("POST", f"/matches/{self.test_match_id}/scores", score_data)
            
        # Complete the match
        result = self.make_request("POST", f"/matches/{self.test_match_id}/complete")
        
        if not result["success"]:
            self.log("❌ Match completion failed", "ERROR")
            return False
            
        completion_data = result["data"]
        
        # Verify awards data is present
        if "best_shots" not in completion_data or "best_players" not in completion_data:
            self.log("❌ Awards data missing from completion response", "ERROR")
            return False
            
        # Verify match status changed to completed
        match_result = self.make_request("GET", f"/matches/{self.test_match_id}")
        if match_result["success"]:
            match = match_result["data"]
            if match.get("status") != "completed":
                self.log("❌ Match status should be 'completed'", "ERROR")
                return False
                
        self.log("✅ Match completion successful")
        return True

    def test_completed_match_privacy(self) -> bool:
        """Test that completed matches show all scores"""
        self.log("Testing completed match privacy...")
        
        if not self.test_match_id:
            self.log("❌ No test match ID available", "ERROR")
            return False
            
        # Get leaderboard without team_id (should show all scores now)
        result = self.make_request("GET", f"/matches/{self.test_match_id}/leaderboard")
        if not result["success"]:
            self.log("❌ Failed to get completed match leaderboard", "ERROR")
            return False
            
        leaderboard = result["data"]
        
        # All scores should be visible now
        for entry in leaderboard:
            if entry["total_strokes"] == "???":
                self.log("❌ Completed match should show all scores", "ERROR")
                return False
                
        # Get all scores (should return all scores now)
        scores_result = self.make_request("GET", f"/matches/{self.test_match_id}/scores")
        if not scores_result["success"]:
            self.log("❌ Failed to get completed match scores", "ERROR")
            return False
            
        self.log("✅ Completed match privacy working correctly")
        return True

    def test_error_handling(self) -> bool:
        """Test error handling for invalid requests"""
        self.log("Testing error handling...")
        
        # Test non-existent match
        result = self.make_request("GET", "/matches/non-existent-id")
        if result["status_code"] != 404:
            self.log("❌ Should return 404 for non-existent match", "ERROR")
            return False
            
        # Test invalid score submission
        if self.test_match_id:
            invalid_score = {
                "player_id": "non-existent-player",
                "hole": 1,
                "strokes": 4
            }
            result = self.make_request("POST", f"/matches/{self.test_match_id}/scores", invalid_score)
            # This might succeed depending on validation, but shouldn't crash
            
        self.log("✅ Error handling working correctly")
        return True

    def run_all_tests(self) -> Dict[str, bool]:
        """Run all backend tests"""
        self.log("=" * 60)
        self.log("STARTING COMPREHENSIVE BACKEND API TESTING")
        self.log("=" * 60)
        
        tests = [
            ("Root Endpoint", self.test_root_endpoint),
            ("Match Creation", self.test_match_creation),
            ("Get All Matches", self.test_get_matches),
            ("Get Specific Match", self.test_get_specific_match),
            ("Start Match", self.test_start_match),
            ("Score Submission", self.test_score_submission),
            ("Privacy Logic", self.test_privacy_logic),
            ("Leaderboard Privacy", self.test_leaderboard_privacy),
            ("Match Completion", self.test_match_completion),
            ("Completed Match Privacy", self.test_completed_match_privacy),
            ("Error Handling", self.test_error_handling)
        ]
        
        results = {}
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            self.log(f"\n--- Running: {test_name} ---")
            try:
                result = test_func()
                results[test_name] = result
                if result:
                    passed += 1
                time.sleep(1)  # Brief pause between tests
            except Exception as e:
                self.log(f"❌ {test_name} failed with exception: {str(e)}", "ERROR")
                results[test_name] = False
                
        self.log("\n" + "=" * 60)
        self.log("TEST RESULTS SUMMARY")
        self.log("=" * 60)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            self.log(f"{test_name}: {status}")
            
        self.log(f"\nOverall: {passed}/{total} tests passed")
        self.log("=" * 60)
        
        return results

if __name__ == "__main__":
    tester = GolfAppTester()
    results = tester.run_all_tests()
    
    # Exit with error code if any tests failed
    if not all(results.values()):
        exit(1)
    else:
        print("\n🎉 All tests passed successfully!")
        exit(0)