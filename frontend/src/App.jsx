import { useState, useEffect } from "react";
import axios from "axios";

const API_BASE = "http://127.0.0.1:8000";

// Configure axios to include auth token
axios.defaults.headers.common['Content-Type'] = 'application/json';

// Add response interceptor to handle 401 errors globally
axios.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Clear auth and redirect to login
      localStorage.removeItem("access_token");
      delete axios.defaults.headers.common['Authorization'];
      window.location.reload(); // Reload to show login screen
    }
    return Promise.reject(error);
  }
);

function App() {
  // Authentication states
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);
  const [showLogin, setShowLogin] = useState(true);
  const [loginData, setLoginData] = useState({ username: "", password: "" });
  const [registerData, setRegisterData] = useState({ username: "", email: "", password: "" });
  const [authError, setAuthError] = useState("");

  const [file, setFile] = useState(null);
  const [uploadedFile, setUploadedFile] = useState("");
  const [documents, setDocuments] = useState([]);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [chatHistory, setChatHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState("chat");
  const [sessionId, setSessionId] = useState("");
  
  // New feature states
  const [summary, setSummary] = useState("");
  const [suggestions, setSuggestions] = useState([]);
  const [extractedInfo, setExtractedInfo] = useState("");
  const [comparison, setComparison] = useState("");
  const [compareFile1, setCompareFile1] = useState("");
  const [compareFile2, setCompareFile2] = useState("");
  const [analytics, setAnalytics] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);

  // Check authentication on mount
  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      checkAuth();
    }
  }, []);

  // Initialize session ID
  useEffect(() => {
    if (isAuthenticated) {
      const storedSession = localStorage.getItem("sessionId");
      if (storedSession) {
        setSessionId(storedSession);
      } else {
        const newSession = `session_${Date.now()}`;
        setSessionId(newSession);
        localStorage.setItem("sessionId", newSession);
      }
    }
  }, [isAuthenticated]);

  // Load documents when authenticated
  useEffect(() => {
    if (isAuthenticated) {
      loadDocuments();
      loadAnalytics();
    }
  }, [isAuthenticated]);

  const checkAuth = async () => {
    try {
      const res = await axios.get(`${API_BASE}/auth/me`);
      setUser(res.data);
      setIsAuthenticated(true);
      setShowLogin(false);
    } catch (err) {
      localStorage.removeItem("access_token");
      delete axios.defaults.headers.common['Authorization'];
      setIsAuthenticated(false);
      setShowLogin(true);
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setAuthError("");
    try {
      const res = await axios.post(`${API_BASE}/auth/login/json`, {
        username: loginData.username,
        password: loginData.password
      });
      localStorage.setItem("access_token", res.data.access_token);
      axios.defaults.headers.common['Authorization'] = `Bearer ${res.data.access_token}`;
      setUser({ username: res.data.username, id: res.data.user_id });
      setIsAuthenticated(true);
      setShowLogin(false);
      setLoginData({ username: "", password: "" });
    } catch (err) {
      setAuthError(err.response?.data?.detail || "Login failed");
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setAuthError("");
    try {
      const res = await axios.post(`${API_BASE}/auth/register`, registerData);
      // Auto-login after registration
      const loginRes = await axios.post(`${API_BASE}/auth/login/json`, {
        username: registerData.username,
        password: registerData.password
      });
      localStorage.setItem("access_token", loginRes.data.access_token);
      axios.defaults.headers.common['Authorization'] = `Bearer ${loginRes.data.access_token}`;
      setUser({ username: loginRes.data.username, id: loginRes.data.user_id });
      setIsAuthenticated(true);
      setShowLogin(false);
      setRegisterData({ username: "", email: "", password: "" });
    } catch (err) {
      setAuthError(err.response?.data?.detail || "Registration failed");
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    delete axios.defaults.headers.common['Authorization'];
    setIsAuthenticated(false);
    setUser(null);
    setShowLogin(true);
    setDocuments([]);
    setChatHistory([]);
  };

  const loadDocuments = async () => {
    try {
      const res = await axios.get(`${API_BASE}/documents`, { timeout: 5000 });
      setDocuments(res.data.documents || []);
      if (res.data.documents && res.data.documents.length > 0 && !uploadedFile) {
        setUploadedFile(res.data.documents[0].filename);
      }
    } catch (err) {
      if (err.response?.status === 401) {
        handleLogout();
      } else if (err.code === 'ERR_NETWORK' || err.message.includes('Network Error')) {
        console.error("Backend server is not running. Please start it first.");
      } else {
        console.error("Error loading documents:", err);
      }
    }
  };

  const loadAnalytics = async () => {
    try {
      const res = await axios.get(`${API_BASE}/analytics`, { timeout: 5000 });
      setAnalytics(res.data);
    } catch (err) {
      if (err.response?.status === 401) {
        handleLogout();
      } else if (err.code === 'ERR_NETWORK' || err.message.includes('Network Error')) {
        console.error("Backend server is not running. Please start it first.");
      } else {
        console.error("Error loading analytics:", err);
      }
    }
  };

  const uploadPDF = async () => {
    if (!file) return alert("Please select a PDF");
    const formData = new FormData();
    formData.append("file", file);
    try {
      setLoading(true);
      const res = await axios.post(`${API_BASE}/upload`, formData);
      setUploadedFile(res.data.file.toLowerCase());
      setAnswer("");
      alert("PDF uploaded successfully");
      loadDocuments();
      loadAnalytics();
    } catch (err) {
      alert(err.response?.data?.detail || "Upload failed");
    } finally {
      setLoading(false);
    }
  };

  const deleteDocument = async (filename) => {
    if (!confirm(`Delete ${filename}? This will remove all chat history for this document.`)) return;
    try {
      await axios.delete(`${API_BASE}/documents/${filename}`);
      alert("Document deleted successfully");
      loadDocuments();
      loadAnalytics();
      if (uploadedFile === filename.toLowerCase()) {
        setUploadedFile("");
      }
    } catch (err) {
      alert(err.response?.data?.detail || "Failed to delete document");
    }
  };

  const askQuestion = async () => {
    if (!question || !uploadedFile) return;
    try {
      setLoading(true);
      
      // Build conversation history from current chat history for follow-up questions
      // Get last 5 exchanges for context (excluding the current question)
      const recentHistory = chatHistory
        .filter(chat => chat.filename === uploadedFile.toLowerCase())
        .slice(-5)  // Last 5 exchanges
        .map(chat => ({
          query: chat.query,
          answer: chat.answer
        }));
      
      const res = await axios.post(`${API_BASE}/chat`, {
        query: question,
        filename: uploadedFile,
        session_id: sessionId,
        conversation_history: recentHistory.length > 0 ? recentHistory : undefined,
      });
      
      setAnswer(res.data.answer);
      setQuestion("");
      loadChatHistory();
      loadAnalytics();
    } catch (err) {
      setAnswer(err.response?.data?.detail || "Error getting answer");
    } finally {
      setLoading(false);
    }
  };

  const loadChatHistory = async () => {
    try {
      const res = await axios.get(
        `${API_BASE}/chat/history?session_id=${sessionId}&limit=20`
      );
      setChatHistory(res.data.history || []);
    } catch (err) {
      console.error("Error loading chat history:", err);
    }
  };

  const getSummary = async () => {
    if (!uploadedFile) return alert("Select a document first");
    try {
      setLoading(true);
      const res = await axios.post(`${API_BASE}/documents/${uploadedFile}/summarize`);
      setSummary(res.data.summary);
    } catch (err) {
      setSummary(err.response?.data?.detail || "Error generating summary");
    } finally {
      setLoading(false);
    }
  };

  const getSuggestions = async () => {
    if (!uploadedFile) return alert("Select a document first");
    try {
      setLoading(true);
      const res = await axios.get(`${API_BASE}/documents/${uploadedFile}/suggestions?count=5`);
      setSuggestions(res.data.suggestions || []);
    } catch (err) {
      setSuggestions([]);
    } finally {
      setLoading(false);
    }
  };

  const extractInfo = async () => {
    if (!uploadedFile) return alert("Select a document first");
    try {
      setLoading(true);
      const res = await axios.post(`${API_BASE}/documents/${uploadedFile}/extract`);
      setExtractedInfo(res.data.extracted_info || "No information extracted");
    } catch (err) {
      setExtractedInfo(err.response?.data?.detail || "Error extracting information");
    } finally {
      setLoading(false);
    }
  };

  const compareDocs = async () => {
    if (!compareFile1 || !compareFile2) return alert("Select both documents");
    try {
      setLoading(true);
      const res = await axios.post(`${API_BASE}/documents/compare`, {
        filename1: compareFile1,
        filename2: compareFile2,
      });
      setComparison(res.data.comparison);
    } catch (err) {
      setComparison(err.response?.data?.detail || "Error comparing documents");
    } finally {
      setLoading(false);
    }
  };

  const searchDocuments = async () => {
    if (!searchQuery.trim()) return;
    try {
      setLoading(true);
      const res = await axios.get(`${API_BASE}/search?query=${encodeURIComponent(searchQuery)}&limit=10`);
      setSearchResults(res.data.results || []);
    } catch (err) {
      setSearchResults([]);
    } finally {
      setLoading(false);
    }
  };

  const selectDocument = (filename) => {
    setUploadedFile(filename.toLowerCase());
    setAnswer("");
    setSummary("");
    setExtractedInfo("");
    loadChatHistory();
  };

  // Show login/register if not authenticated
  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50 flex items-center justify-center">
        <div className="bg-white p-8 rounded-xl shadow-lg max-w-md w-full">
          <h1 className="text-3xl font-bold text-blue-600 mb-2 text-center">🔐 SecureSphere</h1>
          <p className="text-sm text-gray-600 text-center mb-6">AI-powered document Q&A system</p>
          
          <div className="flex gap-2 mb-4">
            <button
              onClick={() => setShowLogin(true)}
              className={`flex-1 py-2 rounded-lg font-medium ${
                showLogin ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-700"
              }`}
            >
              Login
            </button>
            <button
              onClick={() => setShowLogin(false)}
              className={`flex-1 py-2 rounded-lg font-medium ${
                !showLogin ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-700"
              }`}
            >
              Register
            </button>
          </div>

          {showLogin ? (
            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Username</label>
                <input
                  type="text"
                  value={loginData.username}
                  onChange={(e) => setLoginData({ ...loginData, username: e.target.value })}
                  className="w-full border border-gray-300 rounded-lg p-3"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Password</label>
                <input
                  type="password"
                  value={loginData.password}
                  onChange={(e) => setLoginData({ ...loginData, password: e.target.value })}
                  className="w-full border border-gray-300 rounded-lg p-3"
                  required
                />
              </div>
              {authError && (
                <div className="bg-red-50 border border-red-200 text-red-700 p-3 rounded-lg text-sm">
                  {authError}
                </div>
              )}
              <button
                type="submit"
                className="w-full bg-blue-600 text-white px-4 py-3 rounded-lg hover:bg-blue-700 transition"
              >
                Login
              </button>
            </form>
          ) : (
            <form onSubmit={handleRegister} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Username</label>
                <input
                  type="text"
                  value={registerData.username}
                  onChange={(e) => setRegisterData({ ...registerData, username: e.target.value })}
                  className="w-full border border-gray-300 rounded-lg p-3"
                  required
                  minLength={3}
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Email</label>
                <input
                  type="email"
                  value={registerData.email}
                  onChange={(e) => setRegisterData({ ...registerData, email: e.target.value })}
                  className="w-full border border-gray-300 rounded-lg p-3"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Password</label>
                <input
                  type="password"
                  value={registerData.password}
                  onChange={(e) => setRegisterData({ ...registerData, password: e.target.value })}
                  className="w-full border border-gray-300 rounded-lg p-3"
                  required
                  minLength={8}
                />
                <p className="text-xs text-gray-500 mt-1">Minimum 8 characters</p>
              </div>
              {authError && (
                <div className="bg-red-50 border border-red-200 text-red-700 p-3 rounded-lg text-sm">
                  {authError}
                </div>
              )}
              <button
                type="submit"
                className="w-full bg-green-600 text-white px-4 py-3 rounded-lg hover:bg-green-700 transition"
              >
                Register
              </button>
            </form>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-blue-600 mb-1">🔐 SecureSphere</h1>
            <p className="text-sm text-gray-600">AI-powered document Q&A system</p>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-600">Welcome, <strong>{user?.username}</strong></span>
            <button
              onClick={handleLogout}
              className="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 transition text-sm"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto p-4">
        {/* Tabs */}
        <div className="flex flex-wrap gap-2 mb-6 bg-white p-2 rounded-lg shadow-sm">
          {[
            { id: "chat", label: "💬 Chat", icon: "💬" },
            { id: "documents", label: "📄 Documents", icon: "📄" },
            { id: "analyze", label: "🔍 Analyze", icon: "🔍" },
            { id: "compare", label: "⚖️ Compare", icon: "⚖️" },
            { id: "analytics", label: "📊 Analytics", icon: "📊" },
            { id: "search", label: "🔎 Search", icon: "🔎" },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 rounded-lg font-medium transition ${
                activeTab === tab.id
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Chat Tab */}
        {activeTab === "chat" && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {/* Left Sidebar - Documents */}
            <div className="lg:col-span-1 space-y-4">
              <div className="bg-white p-6 rounded-xl shadow-md">
                <h2 className="text-xl font-semibold mb-4">📄 Documents</h2>
                <div className="space-y-2 max-h-96 overflow-y-auto">
                  {documents.length === 0 ? (
                    <p className="text-gray-500 text-sm">No documents uploaded</p>
                  ) : (
                    documents.map((doc) => (
                      <div
                        key={doc.filename}
                        className={`p-3 rounded-lg border cursor-pointer transition ${
                          uploadedFile === doc.filename.toLowerCase()
                            ? "bg-blue-50 border-blue-300"
                            : "bg-gray-50 border-gray-200 hover:bg-gray-100"
                        }`}
                        onClick={() => selectDocument(doc.filename)}
                      >
                        <div className="flex justify-between items-center">
                          <span className="text-sm font-medium truncate flex-1">
                            {doc.filename}
                          </span>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              deleteDocument(doc.filename);
                            }}
                            className="text-red-500 hover:text-red-700 text-xs ml-2"
                            title="Delete"
                          >
                            ✕
                          </button>
                        </div>
                        <p className="text-xs text-gray-500 mt-1">
                          {doc.chunks_count || 0} chunks
                        </p>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* Upload Section */}
              <div className="bg-white p-6 rounded-xl shadow-md">
                <h2 className="text-xl font-semibold mb-4">📤 Upload PDF</h2>
                <input
                  type="file"
                  accept="application/pdf"
                  onChange={(e) => setFile(e.target.files[0])}
                  className="mb-3 w-full border border-gray-300 rounded-lg p-2 text-sm"
                />
                <button
                  onClick={uploadPDF}
                  disabled={loading || !file}
                  className="w-full bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:bg-gray-400 transition"
                >
                  {loading ? "Uploading..." : "Upload PDF"}
                </button>
                {uploadedFile && (
                  <p className="text-sm text-green-600 mt-2">✓ Active: {uploadedFile}</p>
                )}
              </div>
            </div>

            {/* Main Chat Area */}
            <div className="lg:col-span-2 space-y-4">
              <div className="bg-white p-6 rounded-xl shadow-md">
                <div className="flex justify-between items-center mb-4">
                  <h2 className="text-xl font-semibold">💬 Chat</h2>
                  <button
                    onClick={getSuggestions}
                    className="text-sm text-blue-600 hover:underline"
                  >
                    Get Suggestions →
                  </button>
                </div>

                {suggestions.length > 0 && (
                  <div className="bg-blue-50 p-3 rounded-lg mb-4">
                    <p className="text-sm font-semibold mb-2">Suggested Questions:</p>
                    {suggestions.map((s, i) => (
                      <button
                        key={i}
                        onClick={() => setQuestion(s)}
                        className="block text-sm text-blue-700 hover:text-blue-900 mb-1 text-left w-full"
                      >
                        • {s}
                      </button>
                    ))}
                  </div>
                )}

                <div className="mb-4">
                  <div className="flex gap-2 mb-2">
                    <input
                      type="text"
                      placeholder="Ask a question about the document..."
                      value={question}
                      onChange={(e) => setQuestion(e.target.value)}
                      onKeyPress={(e) => e.key === "Enter" && !loading && askQuestion()}
                      className="flex-1 border border-gray-300 rounded-lg p-3 focus:ring-2 focus:ring-blue-500"
                      disabled={!uploadedFile || loading}
                    />
                    <button
                      onClick={askQuestion}
                      disabled={!uploadedFile || loading || !question}
                      className="bg-green-600 text-white px-6 py-3 rounded-lg hover:bg-green-700 disabled:bg-gray-400 transition"
                    >
                      {loading ? "..." : "Ask"}
                    </button>
                  </div>
                  {chatHistory.filter(c => c.filename === uploadedFile.toLowerCase()).length > 0 && (
                    <p className="text-xs text-gray-500 italic">
                      💬 Follow-up questions work! The AI remembers our conversation.
                    </p>
                  )}
                </div>

                {answer && (
                  <div className="bg-blue-50 border border-blue-200 p-4 rounded-lg mb-4">
                    <h3 className="font-semibold mb-2 text-blue-800">Answer:</h3>
                    <p className="text-gray-800 whitespace-pre-wrap">{answer}</p>
                  </div>
                )}
              </div>

              {/* Chat History */}
              <div className="bg-white p-6 rounded-xl shadow-md">
                <div className="flex justify-between items-center mb-4">
                  <h2 className="text-xl font-semibold">📜 Chat History</h2>
                  <button
                    onClick={loadChatHistory}
                    className="text-sm text-blue-600 hover:underline"
                  >
                    Refresh
                  </button>
                </div>
                <p className="text-xs text-gray-500 mb-3">
                  💡 Tip: Ask follow-up questions! The AI remembers previous conversation.
                </p>
                <div className="space-y-3 max-h-96 overflow-y-auto">
                  {chatHistory.length === 0 ? (
                    <p className="text-gray-500 text-sm">No chat history</p>
                  ) : (
                    chatHistory
                      .filter(chat => chat.filename === uploadedFile.toLowerCase())
                      .map((chat) => (
                        <div key={chat.id} className="border border-gray-200 rounded-lg p-3 bg-gray-50 hover:bg-gray-100 transition">
                          <div className="text-xs text-gray-500 mb-1">
                            {new Date(chat.created_at).toLocaleString()}
                            {chat.response_time && (
                              <span className="ml-2">• {chat.response_time.toFixed(1)}s</span>
                            )}
                          </div>
                          <div className="font-medium text-sm mb-1 text-blue-700">Q: {chat.query || chat.question}</div>
                          <div className="text-sm text-gray-700">A: {chat.answer}</div>
                        </div>
                      ))
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Documents Tab */}
        {activeTab === "documents" && (
          <div className="bg-white p-6 rounded-xl shadow-md">
            <h2 className="text-2xl font-semibold mb-4">📄 Document Management</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {documents.map((doc) => (
                <div key={doc.filename} className="border border-gray-200 rounded-lg p-4">
                  <h3 className="font-semibold mb-2 truncate">{doc.filename}</h3>
                  <div className="text-sm text-gray-600 space-y-1">
                    <p>Chunks: {doc.chunks_count || 0}</p>
                    <p>Size: {doc.file_size ? (doc.file_size / 1024).toFixed(2) + " KB" : "N/A"}</p>
                    <p>Uploaded: {doc.uploaded_at ? new Date(doc.uploaded_at).toLocaleDateString() : "N/A"}</p>
                  </div>
                  <div className="flex gap-2 mt-4">
                    <button
                      onClick={() => selectDocument(doc.filename)}
                      className="flex-1 bg-blue-600 text-white px-3 py-2 rounded text-sm hover:bg-blue-700"
                    >
                      Select
                    </button>
                    <button
                      onClick={() => deleteDocument(doc.filename)}
                      className="bg-red-600 text-white px-3 py-2 rounded text-sm hover:bg-red-700"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Analyze Tab */}
        {activeTab === "analyze" && (
          <div className="space-y-4">
            <div className="bg-white p-6 rounded-xl shadow-md">
              <h2 className="text-2xl font-semibold mb-4">🔍 Document Analysis</h2>
              {!uploadedFile && (
                <p className="text-gray-500 mb-4">Select a document from the Chat tab first</p>
              )}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <button
                  onClick={getSummary}
                  disabled={!uploadedFile || loading}
                  className="bg-purple-600 text-white px-6 py-3 rounded-lg hover:bg-purple-700 disabled:bg-gray-400 transition"
                >
                  📄 Generate Summary
                </button>
                <button
                  onClick={extractInfo}
                  disabled={!uploadedFile || loading}
                  className="bg-orange-600 text-white px-6 py-3 rounded-lg hover:bg-orange-700 disabled:bg-gray-400 transition"
                >
                  🔎 Extract Key Info
                </button>
                <button
                  onClick={getSuggestions}
                  disabled={!uploadedFile || loading}
                  className="bg-indigo-600 text-white px-6 py-3 rounded-lg hover:bg-indigo-700 disabled:bg-gray-400 transition"
                >
                  💡 Get Questions
                </button>
              </div>

              {summary && (
                <div className="mt-4 bg-purple-50 p-4 rounded-lg border border-purple-200">
                  <h3 className="font-semibold mb-2 text-purple-800">Summary:</h3>
                  <p className="text-gray-800 whitespace-pre-wrap">{summary}</p>
                </div>
              )}

              {extractedInfo && (
                <div className="mt-4 bg-orange-50 p-4 rounded-lg border border-orange-200">
                  <h3 className="font-semibold mb-2 text-orange-800">Extracted Information:</h3>
                  <p className="text-gray-800 whitespace-pre-wrap">{extractedInfo}</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Compare Tab */}
        {activeTab === "compare" && (
          <div className="bg-white p-6 rounded-xl shadow-md">
            <h2 className="text-2xl font-semibold mb-4">⚖️ Compare Documents</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
              <div>
                <label className="block text-sm font-medium mb-2">Document 1:</label>
                <select
                  value={compareFile1}
                  onChange={(e) => setCompareFile1(e.target.value)}
                  className="w-full border border-gray-300 rounded-lg p-3"
                >
                  <option value="">Select document...</option>
                  {documents.map((doc) => (
                    <option key={doc.filename} value={doc.filename}>
                      {doc.filename}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Document 2:</label>
                <select
                  value={compareFile2}
                  onChange={(e) => setCompareFile2(e.target.value)}
                  className="w-full border border-gray-300 rounded-lg p-3"
                >
                  <option value="">Select document...</option>
                  {documents.map((doc) => (
                    <option key={doc.filename} value={doc.filename}>
                      {doc.filename}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <button
              onClick={compareDocs}
              disabled={!compareFile1 || !compareFile2 || loading}
              className="w-full bg-red-600 text-white px-6 py-3 rounded-lg hover:bg-red-700 disabled:bg-gray-400 transition mb-4"
            >
              Compare Documents
            </button>
            {comparison && (
              <div className="bg-red-50 p-4 rounded-lg border border-red-200">
                <h3 className="font-semibold mb-2 text-red-800">Comparison:</h3>
                <p className="text-gray-800 whitespace-pre-wrap">{comparison}</p>
              </div>
            )}
          </div>
        )}

        {/* Analytics Tab */}
        {activeTab === "analytics" && analytics && (
          <div className="bg-white p-6 rounded-xl shadow-md">
            <h2 className="text-2xl font-semibold mb-4">📊 Analytics & Statistics</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              <div className="bg-blue-50 p-4 rounded-lg">
                <h3 className="text-sm font-medium text-gray-600">Total Documents</h3>
                <p className="text-3xl font-bold text-blue-600">{analytics.total_documents}</p>
              </div>
              <div className="bg-green-50 p-4 rounded-lg">
                <h3 className="text-sm font-medium text-gray-600">Total Chats</h3>
                <p className="text-3xl font-bold text-green-600">{analytics.total_chats}</p>
              </div>
              <div className="bg-purple-50 p-4 rounded-lg">
                <h3 className="text-sm font-medium text-gray-600">Avg Response Time</h3>
                <p className="text-3xl font-bold text-purple-600">
                  {analytics.average_response_time ? `${analytics.average_response_time}s` : "N/A"}
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <h3 className="font-semibold mb-2">Most Asked Questions</h3>
                <div className="space-y-2">
                  {analytics.most_asked_questions?.map((q, i) => (
                    <div key={i} className="bg-gray-50 p-3 rounded">
                      <p className="text-sm font-medium">{q.question}</p>
                      <p className="text-xs text-gray-500">{q.count} times</p>
                    </div>
                  ))}
                </div>
              </div>
              <div>
                <h3 className="font-semibold mb-2">Popular Documents</h3>
                <div className="space-y-2">
                  {analytics.popular_documents?.map((doc, i) => (
                    <div key={i} className="bg-gray-50 p-3 rounded">
                      <p className="text-sm font-medium">{doc.filename}</p>
                      <p className="text-xs text-gray-500">{doc.chat_count} chats</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Search Tab */}
        {activeTab === "search" && (
          <div className="bg-white p-6 rounded-xl shadow-md">
            <h2 className="text-2xl font-semibold mb-4">🔎 Search Documents</h2>
            <div className="flex gap-2 mb-4">
              <input
                type="text"
                placeholder="Search for documents by content..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyPress={(e) => e.key === "Enter" && searchDocuments()}
                className="flex-1 border border-gray-300 rounded-lg p-3"
              />
              <button
                onClick={searchDocuments}
                disabled={loading}
                className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 disabled:bg-gray-400"
              >
                Search
              </button>
            </div>
            {searchResults.length > 0 && (
              <div className="space-y-2">
                <h3 className="font-semibold">Search Results ({searchResults.length}):</h3>
                {searchResults.map((result, i) => (
                  <div key={i} className="border border-gray-200 rounded-lg p-3 bg-gray-50">
                    <p className="font-medium">{result.filename}</p>
                    <p className="text-sm text-gray-600 mt-1">{result.preview}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {loading && (
          <div className="fixed bottom-4 right-4 bg-blue-600 text-white px-6 py-3 rounded-lg shadow-lg">
            ⏳ Processing...
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
