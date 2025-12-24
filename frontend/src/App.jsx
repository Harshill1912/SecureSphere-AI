import { useState } from "react";
import axios from "axios";

function App() {
  const [file, setFile] = useState(null);
  const [uploadedFile, setUploadedFile] = useState("");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);

  // ===============================
  // UPLOAD PDF
  // ===============================
  const uploadPDF = async () => {
    if (!file) return alert("Please select a PDF");

    const formData = new FormData();
    formData.append("file", file);

    try {
      setLoading(true);
      const res = await axios.post(
        "http://127.0.0.1:8000/upload",
        formData
      );

      setUploadedFile(res.data.file.toLowerCase());
      setAnswer("");
      alert("PDF uploaded successfully");
    } catch (err) {
      alert("Upload failed");
      console.log(err);
    } finally {
      setLoading(false);
    }
  };

  // ===============================
  // ASK QUESTION (FAST – POST)
  // ===============================
 const askQuestion = async () => {
  if (!question) return;
  if (!uploadedFile) return alert("Upload a PDF first");

  try {
    setLoading(true);

    const res = await axios.post(
      "http://127.0.0.1:8000/chat",
      {
        query: question,
        filename: uploadedFile.toLowerCase(), 
      }
    );

    setAnswer(res.data.answer);
  } catch (err) {
    setAnswer("Error getting answer");
    console.log(err);
  } finally {
    setLoading(false);
  }
};

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col items-center p-4">
      <h1 className="text-3xl font-bold text-blue-600 mb-2">
        🔐 SecureSphere
      </h1>
      <p className="mb-6 text-gray-700">
        AI-powered document question answering
      </p>

      {/* Upload */}
      <div className="bg-white p-6 rounded-lg shadow-md w-full max-w-md mb-4">
        <input
          type="file"
          accept="application/pdf"
          onChange={(e) => setFile(e.target.files[0])}
          className="mb-4 w-full border border-gray-300 rounded p-2"
        />
        <button
          onClick={uploadPDF}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 w-full"
        >
          Upload PDF
        </button>

        {uploadedFile && (
          <p className="text-sm text-green-600 mt-2">
            📄 Active file: {uploadedFile}
          </p>
        )}
      </div>

      {/* Ask */}
      <div className="bg-white p-6 rounded-lg shadow-md w-full max-w-md mb-4">
        <input
          type="text"
          placeholder="Ask a question about the document..."
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          className="mb-4 w-full border border-gray-300 rounded p-2"
        />
        <button
          onClick={askQuestion}
          className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 w-full"
        >
          Ask
        </button>
      </div>

      {loading && (
        <p className="text-gray-500 mt-2">⏳ Processing...</p>
      )}

      {answer && (
        <div className="bg-gray-200 p-4 rounded-lg shadow-md w-full max-w-md mt-4">
          <h3 className="font-semibold mb-2">Answer:</h3>
          <p>{answer}</p>
        </div>
      )}
    </div>
  );
}

export default App;
