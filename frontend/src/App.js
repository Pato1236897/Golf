import React, { useState, useEffect, useRef } from 'react';
import './App.css';
import axios from 'axios';
import io from 'socket.io-client';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Golf App Main Component
function App() {
  const [currentView, setCurrentView] = useState('home'); // home, create-match, match, leaderboard
  const [matches, setMatches] = useState([]);
  const [currentMatch, setCurrentMatch] = useState(null);
  const [currentTeam, setCurrentTeam] = useState(null);
  const [currentPlayer, setCurrentPlayer] = useState(null);
  const [scores, setScores] = useState([]);
  const [leaderboard, setLeaderboard] = useState([]);
  const [socket, setSocket] = useState(null);
  const [loading, setLoading] = useState(false);

  // Create match form state
  const [matchForm, setMatchForm] = useState({
    name: '',
    matchType: 'stroke_play',
    holes: 18,
    teams: [
      { name: 'Team 1', color: '#3B82F6', players: [{ name: '', email: '', handicap: 0 }] },
      { name: 'Team 2', color: '#EF4444', players: [{ name: '', email: '', handicap: 0 }] }
    ]
  });

  // Score input state
  const [scoreInput, setScoreInput] = useState({
    hole: 1,
    strokes: 1,
    putts: 0,
    penalties: 0,
    bestShot: false,
    bestShotDescription: ''
  });

  // Load matches on component mount
  useEffect(() => {
    loadMatches();
  }, []);

  // Setup WebSocket connection
  useEffect(() => {
    if (currentMatch && currentPlayer) {
      const newSocket = io(BACKEND_URL, {
        transports: ['websocket']
      });
      
      newSocket.emit('join_match', {
        match_id: currentMatch.id,
        user_id: currentPlayer.id
      });

      newSocket.on('score_update', (data) => {
        loadMatchScores();
        loadLeaderboard();
      });

      newSocket.on('match_completed', (data) => {
        setCurrentView('leaderboard');
        loadLeaderboard();
      });

      setSocket(newSocket);

      return () => {
        newSocket.disconnect();
      };
    }
  }, [currentMatch, currentPlayer]);

  const loadMatches = async () => {
    try {
      const response = await axios.get(`${API}/matches`);
      setMatches(response.data);
    } catch (error) {
      console.error('Error loading matches:', error);
    }
  };

  const loadMatchScores = async () => {
    if (!currentMatch || !currentTeam) return;
    
    try {
      const response = await axios.get(`${API}/matches/${currentMatch.id}/scores?team_id=${currentTeam.id}`);
      setScores(response.data);
    } catch (error) {
      console.error('Error loading scores:', error);
    }
  };

  const loadLeaderboard = async () => {
    if (!currentMatch) return;
    
    try {
      const response = await axios.get(`${API}/matches/${currentMatch.id}/leaderboard?team_id=${currentTeam?.id}`);
      setLeaderboard(response.data);
    } catch (error) {
      console.error('Error loading leaderboard:', error);
    }
  };

  const createMatch = async () => {
    setLoading(true);
    try {
      const creatorId = `user_${Date.now()}`;
      const response = await axios.post(`${API}/matches`, {
        ...matchForm,
        creator_id: creatorId
      });
      
      setCurrentMatch(response.data);
      setCurrentView('match');
      await loadMatches();
    } catch (error) {
      console.error('Error creating match:', error);
      alert('Failed to create match');
    }
    setLoading(false);
  };

  const joinMatch = async (match) => {
    setCurrentMatch(match);
    setCurrentView('team-select');
  };

  const selectTeamAndPlayer = (team, player) => {
    setCurrentTeam(team);
    setCurrentPlayer(player);
    setCurrentView('match');
    loadMatchScores();
    loadLeaderboard();
  };

  const startMatch = async () => {
    try {
      await axios.post(`${API}/matches/${currentMatch.id}/start`);
      const updatedMatch = { ...currentMatch, status: 'in_progress' };
      setCurrentMatch(updatedMatch);
    } catch (error) {
      console.error('Error starting match:', error);
    }
  };

  const submitScore = async () => {
    if (!currentPlayer || !currentMatch) return;
    
    setLoading(true);
    try {
      await axios.post(`${API}/matches/${currentMatch.id}/scores`, {
        player_id: currentPlayer.id,
        ...scoreInput
      });
      
      // Reset form for next hole
      setScoreInput({
        hole: scoreInput.hole + 1,
        strokes: 1,
        putts: 0,
        penalties: 0,
        bestShot: false,
        bestShotDescription: ''
      });
      
      await loadMatchScores();
      await loadLeaderboard();
    } catch (error) {
      console.error('Error submitting score:', error);
      alert('Failed to submit score');
    }
    setLoading(false);
  };

  const completeMatch = async () => {
    try {
      await axios.post(`${API}/matches/${currentMatch.id}/complete`);
      setCurrentView('leaderboard');
      await loadLeaderboard();
    } catch (error) {
      console.error('Error completing match:', error);
    }
  };

  const addPlayerToTeam = (teamIndex) => {
    const updatedTeams = [...matchForm.teams];
    if (updatedTeams[teamIndex].players.length < 4) {
      updatedTeams[teamIndex].players.push({ name: '', email: '', handicap: 0 });
      setMatchForm({ ...matchForm, teams: updatedTeams });
    }
  };

  const updatePlayer = (teamIndex, playerIndex, field, value) => {
    const updatedTeams = [...matchForm.teams];
    updatedTeams[teamIndex].players[playerIndex][field] = value;
    setMatchForm({ ...matchForm, teams: updatedTeams });
  };

  const updateTeam = (teamIndex, field, value) => {
    const updatedTeams = [...matchForm.teams];
    updatedTeams[teamIndex][field] = value;
    setMatchForm({ ...matchForm, teams: updatedTeams });
  };

  // Home View
  const HomeView = () => (
    <div className="min-h-screen bg-gradient-to-br from-green-50 to-green-100 p-4">
      <div className="max-w-md mx-auto">
        <div className="text-center mb-8">
          <div className="text-6xl mb-4">⛳</div>
          <h1 className="text-3xl font-bold text-green-800 mb-2">Golf Scorer</h1>
          <p className="text-green-600">Team match scoring with live updates</p>
        </div>

        <div className="space-y-4">
          <button
            onClick={() => setCurrentView('create-match')}
            className="w-full bg-green-600 text-white py-4 px-6 rounded-xl font-semibold text-lg shadow-lg hover:bg-green-700 transition-colors"
          >
            🏆 Create New Match
          </button>

          <div className="bg-white rounded-xl p-6 shadow-lg">
            <h2 className="text-xl font-semibold mb-4 text-gray-800">Recent Matches</h2>
            {matches.length === 0 ? (
              <p className="text-gray-500 text-center py-4">No matches yet</p>
            ) : (
              <div className="space-y-3">
                {matches.slice(0, 5).map((match) => (
                  <div
                    key={match.id}
                    onClick={() => joinMatch(match)}
                    className="flex justify-between items-center p-3 bg-gray-50 rounded-lg cursor-pointer hover:bg-gray-100 transition-colors"
                  >
                    <div>
                      <div className="font-medium text-gray-800">{match.name}</div>
                      <div className="text-sm text-gray-500">
                        {match.holes} holes • {match.teams.length} teams
                      </div>
                    </div>
                    <div className={`px-3 py-1 rounded-full text-xs font-medium ${
                      match.status === 'completed' ? 'bg-gray-200 text-gray-700' :
                      match.status === 'in_progress' ? 'bg-green-200 text-green-700' :
                      'bg-blue-200 text-blue-700'
                    }`}>
                      {match.status === 'completed' ? 'Finished' :
                       match.status === 'in_progress' ? 'Live' : 'Setup'}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );

  // Create Match View
  const CreateMatchView = () => (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-blue-100 p-4">
      <div className="max-w-2xl mx-auto">
        <div className="bg-white rounded-xl p-6 shadow-lg">
          <div className="flex items-center mb-6">
            <button
              onClick={() => setCurrentView('home')}
              className="mr-4 p-2 text-gray-600 hover:text-gray-800"
            >
              ← Back
            </button>
            <h1 className="text-2xl font-bold text-gray-800">Create New Match</h1>
          </div>

          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Match Name</label>
              <input
                type="text"
                value={matchForm.name}
                onChange={(e) => setMatchForm({ ...matchForm, name: e.target.value })}
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="e.g., Sunday Tournament"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Match Type</label>
                <select
                  value={matchForm.matchType}
                  onChange={(e) => setMatchForm({ ...matchForm, matchType: e.target.value })}
                  className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="stroke_play">Stroke Play</option>
                  <option value="scramble">Scramble</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Holes</label>
                <select
                  value={matchForm.holes}
                  onChange={(e) => setMatchForm({ ...matchForm, holes: parseInt(e.target.value) })}
                  className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value={9}>9 Holes</option>
                  <option value={18}>18 Holes</option>
                </select>
              </div>
            </div>

            {/* Teams Setup */}
            <div>
              <h2 className="text-lg font-semibold text-gray-800 mb-4">Teams</h2>
              {matchForm.teams.map((team, teamIndex) => (
                <div key={teamIndex} className="mb-6 p-4 border border-gray-200 rounded-lg">
                  <div className="grid grid-cols-2 gap-4 mb-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Team Name</label>
                      <input
                        type="text"
                        value={team.name}
                        onChange={(e) => updateTeam(teamIndex, 'name', e.target.value)}
                        className="w-full p-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Team Color</label>
                      <input
                        type="color"
                        value={team.color}
                        onChange={(e) => updateTeam(teamIndex, 'color', e.target.value)}
                        className="w-full h-10 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      />
                    </div>
                  </div>

                  <div className="space-y-3">
                    <label className="block text-sm font-medium text-gray-700">Players</label>
                    {team.players.map((player, playerIndex) => (
                      <div key={playerIndex} className="grid grid-cols-3 gap-2">
                        <input
                          type="text"
                          placeholder="Player name"
                          value={player.name}
                          onChange={(e) => updatePlayer(teamIndex, playerIndex, 'name', e.target.value)}
                          className="p-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        />
                        <input
                          type="email"
                          placeholder="Email (optional)"
                          value={player.email}
                          onChange={(e) => updatePlayer(teamIndex, playerIndex, 'email', e.target.value)}
                          className="p-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        />
                        <input
                          type="number"
                          placeholder="Handicap"
                          value={player.handicap}
                          onChange={(e) => updatePlayer(teamIndex, playerIndex, 'handicap', parseInt(e.target.value) || 0)}
                          className="p-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        />
                      </div>
                    ))}
                    {team.players.length < 4 && (
                      <button
                        onClick={() => addPlayerToTeam(teamIndex)}
                        className="text-blue-600 hover:text-blue-700 text-sm font-medium"
                      >
                        + Add Player
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>

            <button
              onClick={createMatch}
              disabled={loading || !matchForm.name || matchForm.teams.every(t => t.players.every(p => !p.name))}
              className="w-full bg-blue-600 text-white py-3 px-6 rounded-lg font-semibold hover:bg-blue-700 transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed"
            >
              {loading ? 'Creating...' : 'Create Match'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );

  // Team Selection View
  const TeamSelectView = () => (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 to-purple-100 p-4">
      <div className="max-w-md mx-auto">
        <div className="bg-white rounded-xl p-6 shadow-lg">
          <div className="flex items-center mb-6">
            <button
              onClick={() => setCurrentView('home')}
              className="mr-4 p-2 text-gray-600 hover:text-gray-800"
            >
              ← Back
            </button>
            <h1 className="text-xl font-bold text-gray-800">Join Match</h1>
          </div>

          <div className="text-center mb-6">
            <h2 className="text-2xl font-bold text-gray-800 mb-2">{currentMatch?.name}</h2>
            <p className="text-gray-600">{currentMatch?.holes} holes • {currentMatch?.match_type}</p>
          </div>

          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-gray-800">Select Your Team & Player</h3>
            {currentMatch?.teams.map((team) => (
              <div key={team.id} className="border border-gray-200 rounded-lg p-4">
                <div className="flex items-center mb-3">
                  <div
                    className="w-4 h-4 rounded-full mr-3"
                    style={{ backgroundColor: team.color }}
                  ></div>
                  <h4 className="font-semibold text-gray-800">{team.name}</h4>
                </div>
                <div className="space-y-2">
                  {team.players.map((player) => (
                    <button
                      key={player.id}
                      onClick={() => selectTeamAndPlayer(team, player)}
                      className="w-full text-left p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                    >
                      <div className="font-medium text-gray-800">{player.name}</div>
                      {player.handicap > 0 && (
                        <div className="text-sm text-gray-500">Handicap: {player.handicap}</div>
                      )}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );

  // Match View (Live Scoring)
  const MatchView = () => (
    <div className="min-h-screen bg-gradient-to-br from-green-50 to-green-100 p-4">
      <div className="max-w-md mx-auto">
        {/* Header */}
        <div className="bg-white rounded-xl p-4 shadow-lg mb-4">
          <div className="flex justify-between items-center mb-3">
            <button
              onClick={() => setCurrentView('home')}
              className="p-2 text-gray-600 hover:text-gray-800"
            >
              ← Back
            </button>
            <button
              onClick={() => setCurrentView('leaderboard')}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700"
            >
              Leaderboard
            </button>
          </div>
          <div className="text-center">
            <h1 className="text-xl font-bold text-gray-800">{currentMatch?.name}</h1>
            <div className="flex items-center justify-center mt-2">
              <div
                className="w-3 h-3 rounded-full mr-2"
                style={{ backgroundColor: currentTeam?.color }}
              ></div>
              <span className="text-gray-600">{currentPlayer?.name} • {currentTeam?.name}</span>
            </div>
          </div>
        </div>

        {/* Score Input */}
        {currentMatch?.status === 'in_progress' && (
          <div className="bg-white rounded-xl p-6 shadow-lg mb-4">
            <h2 className="text-lg font-semibold text-gray-800 mb-4">
              Hole {scoreInput.hole} Score
            </h2>

            <div className="grid grid-cols-2 gap-4 mb-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Strokes</label>
                <div className="flex items-center">
                  <button
                    onClick={() => setScoreInput({...scoreInput, strokes: Math.max(1, scoreInput.strokes - 1)})}
                    className="p-2 bg-gray-200 rounded-l-lg hover:bg-gray-300"
                  >
                    -
                  </button>
                  <div className="px-4 py-2 bg-gray-100 font-semibold text-center min-w-[50px]">
                    {scoreInput.strokes}
                  </div>
                  <button
                    onClick={() => setScoreInput({...scoreInput, strokes: scoreInput.strokes + 1})}
                    className="p-2 bg-gray-200 rounded-r-lg hover:bg-gray-300"
                  >
                    +
                  </button>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Putts</label>
                <div className="flex items-center">
                  <button
                    onClick={() => setScoreInput({...scoreInput, putts: Math.max(0, scoreInput.putts - 1)})}
                    className="p-2 bg-gray-200 rounded-l-lg hover:bg-gray-300"
                  >
                    -
                  </button>
                  <div className="px-4 py-2 bg-gray-100 font-semibold text-center min-w-[50px]">
                    {scoreInput.putts}
                  </div>
                  <button
                    onClick={() => setScoreInput({...scoreInput, putts: scoreInput.putts + 1})}
                    className="p-2 bg-gray-200 rounded-r-lg hover:bg-gray-300"
                  >
                    +
                  </button>
                </div>
              </div>
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">Penalties</label>
              <div className="flex items-center">
                <button
                  onClick={() => setScoreInput({...scoreInput, penalties: Math.max(0, scoreInput.penalties - 1)})}
                  className="p-2 bg-gray-200 rounded-l-lg hover:bg-gray-300"
                >
                  -
                </button>
                <div className="px-4 py-2 bg-gray-100 font-semibold text-center min-w-[50px]">
                  {scoreInput.penalties}
                </div>
                <button
                  onClick={() => setScoreInput({...scoreInput, penalties: scoreInput.penalties + 1})}
                  className="p-2 bg-gray-200 rounded-r-lg hover:bg-gray-300"
                >
                  +
                </button>
              </div>
            </div>

            <div className="mb-4">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={scoreInput.bestShot}
                  onChange={(e) => setScoreInput({...scoreInput, bestShot: e.target.checked})}
                  className="mr-2 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <span className="text-sm font-medium text-gray-700">🏆 Best Shot of the hole</span>
              </label>
              {scoreInput.bestShot && (
                <input
                  type="text"
                  placeholder="Describe the shot..."
                  value={scoreInput.bestShotDescription}
                  onChange={(e) => setScoreInput({...scoreInput, bestShotDescription: e.target.value})}
                  className="mt-2 w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              )}
            </div>

            <button
              onClick={submitScore}
              disabled={loading}
              className="w-full bg-green-600 text-white py-3 px-6 rounded-lg font-semibold hover:bg-green-700 transition-colors disabled:bg-gray-400"
            >
              {loading ? 'Submitting...' : `Submit Hole ${scoreInput.hole} Score`}
            </button>
          </div>
        )}

        {/* Match Controls */}
        {currentMatch?.status === 'setup' && (
          <div className="bg-white rounded-xl p-6 shadow-lg mb-4">
            <button
              onClick={startMatch}
              className="w-full bg-green-600 text-white py-3 px-6 rounded-lg font-semibold hover:bg-green-700 transition-colors"
            >
              🏁 Start Match
            </button>
          </div>
        )}

        {currentMatch?.status === 'in_progress' && scoreInput.hole > currentMatch.holes && (
          <div className="bg-white rounded-xl p-6 shadow-lg mb-4">
            <button
              onClick={completeMatch}
              className="w-full bg-blue-600 text-white py-3 px-6 rounded-lg font-semibold hover:bg-blue-700 transition-colors"
            >
              🏆 Complete Match
            </button>
          </div>
        )}

        {/* Team Scores */}
        <div className="bg-white rounded-xl p-6 shadow-lg">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">
            Team Scores ({currentTeam?.name})
          </h3>
          {scores.length === 0 ? (
            <p className="text-gray-500 text-center py-4">No scores yet</p>
          ) : (
            <div className="space-y-3">
              {currentTeam?.players.map((player) => {
                const playerScores = scores.filter(s => s.player_id === player.id);
                const totalStrokes = playerScores.reduce((sum, s) => sum + s.strokes, 0);
                const holesPlayed = playerScores.length;
                
                return (
                  <div key={player.id} className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                    <div>
                      <div className="font-medium text-gray-800">{player.name}</div>
                      <div className="text-sm text-gray-500">
                        {holesPlayed} holes played
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="font-semibold text-gray-800">{totalStrokes} strokes</div>
                      <div className="text-sm text-gray-500">
                        {holesPlayed > 0 ? (totalStrokes / holesPlayed).toFixed(1) : '0.0'} avg
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );

  // Leaderboard View
  const LeaderboardView = () => (
    <div className="min-h-screen bg-gradient-to-br from-yellow-50 to-yellow-100 p-4">
      <div className="max-w-md mx-auto">
        <div className="bg-white rounded-xl p-6 shadow-lg">
          <div className="flex items-center mb-6">
            <button
              onClick={() => setCurrentView('match')}
              className="mr-4 p-2 text-gray-600 hover:text-gray-800"
            >
              ← Back
            </button>
            <h1 className="text-xl font-bold text-gray-800">Leaderboard</h1>
          </div>

          <div className="text-center mb-6">
            <h2 className="text-2xl font-bold text-gray-800 mb-2">{currentMatch?.name}</h2>
            <div className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${
              currentMatch?.status === 'completed' ? 'bg-green-200 text-green-700' :
              currentMatch?.status === 'in_progress' ? 'bg-blue-200 text-blue-700' :
              'bg-gray-200 text-gray-700'
            }`}>
              {currentMatch?.status === 'completed' ? '🏆 Completed' :
               currentMatch?.status === 'in_progress' ? '🔴 Live' : '⏳ Setup'}
            </div>
          </div>

          {leaderboard.length === 0 ? (
            <p className="text-gray-500 text-center py-8">No scores available yet</p>
          ) : (
            <div className="space-y-3">
              {leaderboard.map((player, index) => (
                <div
                  key={player.player_id}
                  className="flex items-center justify-between p-4 bg-gray-50 rounded-lg"
                >
                  <div className="flex items-center">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center text-white font-bold text-sm mr-3 ${
                      index === 0 ? 'bg-yellow-500' :
                      index === 1 ? 'bg-gray-400' :
                      index === 2 ? 'bg-orange-600' : 'bg-gray-300'
                    }`}>
                      {index + 1}
                    </div>
                    <div>
                      <div className="font-medium text-gray-800">{player.player_name}</div>
                      <div className="flex items-center text-sm text-gray-500">
                        <div
                          className="w-3 h-3 rounded-full mr-2"
                          style={{ backgroundColor: player.team_color }}
                        ></div>
                        {player.team_name}
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-semibold text-gray-800">
                      {typeof player.total_strokes === 'number' ? player.total_strokes : player.total_strokes} strokes
                    </div>
                    <div className="text-sm text-gray-500">
                      {typeof player.best_shots === 'number' ? player.best_shots : player.best_shots} 🏆
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {currentMatch?.status === 'completed' && (
            <div className="mt-6 p-4 bg-green-50 rounded-lg">
              <h3 className="font-semibold text-green-800 mb-2">🎉 Match Complete!</h3>
              <p className="text-green-600 text-sm">
                Great game everyone! Check out the awards and final standings above.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );

  // Render current view
  const renderCurrentView = () => {
    switch (currentView) {
      case 'home':
        return <HomeView />;
      case 'create-match':
        return <CreateMatchView />;
      case 'team-select':
        return <TeamSelectView />;
      case 'match':
        return <MatchView />;
      case 'leaderboard':
        return <LeaderboardView />;
      default:
        return <HomeView />;
    }
  };

  return renderCurrentView();
}

export default App;