"use client";

import { useState, useEffect } from "react";

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface ChatState {
  conversationStep: string;
  journeyName: string | null;
  documentType: string | null;
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [chatState, setChatState] = useState<ChatState>({
    conversationStep: "initial",
    journeyName: null,
    documentType: null,
  });
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const sessionId = "user-session-1";

  useEffect(() => {
    // Get initial message from backend
    const getInitialMessage = async () => {
      setIsLoading(true);
      try {
        const response = await fetch("http://localhost:8000/api/chat", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ message: "", session_id: sessionId }),
        });

        const data = await response.json();
        const initialMessage: Message = {
          role: "assistant",
          content: data.response,
        };
        setMessages([initialMessage]);
        
        setChatState({
          conversationStep: data.conversation_step,
          journeyName: data.journey_name,
          documentType: data.document_type,
        });
      } catch (error) {
        console.error("Error:", error);
        const errorMessage: Message = {
          role: "assistant",
          content: "Sorry, there was an error connecting to the server.",
        };
        setMessages([errorMessage]);
      } finally {
        setIsLoading(false);
      }
    };
    
    getInitialMessage();
  }, []);

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMessage: Message = { role: "user", content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const response = await fetch("http://localhost:8000/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message: input, session_id: sessionId }),
      });

      const data = await response.json();
      const assistantMessage: Message = {
        role: "assistant",
        content: data.response,
      };
      setMessages((prev) => [...prev, assistantMessage]);
      
      setChatState({
        conversationStep: data.conversation_step,
        journeyName: data.journey_name,
        documentType: data.document_type,
      });
    } catch (error) {
      console.error("Error:", error);
      const errorMessage: Message = {
        role: "assistant",
        content: "Sorry, there was an error processing your request.",
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.name.endsWith('.pdf')) {
      alert('Please upload a PDF file only');
      return;
    }

    setSelectedFile(file);
    setIsLoading(true);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('journey_name', chatState.journeyName || '');
      if (chatState.documentType) {
        formData.append('document_type', chatState.documentType);
      }
      formData.append('session_id', sessionId);

      const response = await fetch('http://localhost:8000/api/upload', {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();
      
      if (data.error) {
        const errorMessage: Message = {
          role: "assistant",
          content: data.error,
        };
        setMessages((prev) => [...prev, errorMessage]);
      } else {
        // Add upload confirmation message
        const uploadMessage: Message = {
          role: "assistant",
          content: data.parse_success 
            ? `Document "${file.name}" uploaded successfully!\n\nDocument parsed: ${data.chunks_count} chunks extracted.`
            : `Document "${file.name}" uploaded successfully!`,
        };
        setMessages((prev) => [...prev, uploadMessage]);
        
        // Now get the next step from backend
        try {
          const chatResponse = await fetch("http://localhost:8000/api/chat", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({ message: "", session_id: sessionId }),
          });
          
          const chatData = await chatResponse.json();
          const nextMessage: Message = {
            role: "assistant",
            content: chatData.response,
          };
          setMessages((prev) => [...prev, nextMessage]);
          
          setChatState({
            conversationStep: chatData.conversation_step,
            journeyName: chatData.journey_name,
            documentType: chatData.document_type,
          });
        } catch (err) {
          console.error("Error getting next step:", err);
        }
      }
    } catch (error) {
      console.error("Error:", error);
      const errorMessage: Message = {
        role: "assistant",
        content: "Sorry, there was an error uploading your document.",
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      setSelectedFile(null);
      e.target.value = '';
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const startNewChat = async () => {
    setIsLoading(true);
    try {
      // Reset session on backend
      await fetch("http://localhost:8000/api/reset", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(sessionId),
      });
      
      // Get fresh initial message
      const response = await fetch("http://localhost:8000/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message: "", session_id: sessionId }),
      });

      const data = await response.json();
      const initialMessage: Message = {
        role: "assistant",
        content: data.response,
      };
      setMessages([initialMessage]);
      setInput("");
      setChatState({
        conversationStep: data.conversation_step,
        journeyName: data.journey_name,
        documentType: data.document_type,
      });
    } catch (error) {
      console.error("Error:", error);
      const errorMessage: Message = {
        role: "assistant",
        content: "Sorry, there was an error resetting the chat.",
      };
      setMessages([errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="flex min-h-screen flex-col bg-gradient-to-b from-gray-900 to-gray-950">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-900/50 backdrop-blur-sm">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <h1 className="text-2xl font-bold text-white">TraceQA</h1>
          <button
            onClick={startNewChat}
            className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-200 rounded-lg transition-colors text-sm font-medium"
          >
            New Chat
          </button>
        </div>
      </header>

      {/* Chat Area */}
      <div className="flex-1 max-w-5xl w-full mx-auto px-6 py-8 overflow-y-auto">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center space-y-6">
            <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl flex items-center justify-center">
              <svg
                className="w-10 h-10 text-white"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
                />
              </svg>
            </div>
            <div>
              <h2 className="text-3xl font-bold text-white mb-2">
                Welcome to TraceQA
              </h2>
              <p className="text-gray-400 max-w-md">
                Your intelligent assistant for managing journeys and documents.
                Click &quot;New Chat&quot; to get started.
              </p>
            </div>
          </div>
        ) : (
          <div className="space-y-6">
            {messages.map((message, index) => (
              <div
                key={index}
                className={`flex ${
                  message.role === "user" ? "justify-end" : "justify-start"
                }`}
              >
                <div
                  className={`max-w-3xl rounded-2xl px-6 py-4 ${
                    message.role === "user"
                      ? "bg-blue-600 text-white"
                      : "bg-gray-800 text-gray-100 border border-gray-700"
                  }`}
                >
                  <p className="whitespace-pre-wrap">{message.content}</p>
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="flex justify-start">
                <div className="max-w-3xl rounded-2xl px-6 py-4 bg-gray-800 border border-gray-700">
                  <div className="flex space-x-2">
                    <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce"></div>
                    <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce delay-100"></div>
                    <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce delay-200"></div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="border-t border-gray-800 bg-gray-900/50 backdrop-blur-sm">
        <div className="max-w-5xl mx-auto px-6 py-4">
          {chatState.conversationStep === "awaiting_document_upload" ? (
            <div className="space-y-3">
              <div className="flex items-center justify-center w-full">
                <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-gray-700 border-dashed rounded-xl cursor-pointer bg-gray-800 hover:bg-gray-750 transition-colors">
                  <div className="flex flex-col items-center justify-center pt-5 pb-6">
                    <svg
                      className="w-10 h-10 mb-3 text-gray-400"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                      />
                    </svg>
                    <p className="mb-2 text-sm text-gray-400">
                      <span className="font-semibold">Click to upload PDF</span> or drag and drop
                    </p>
                    <p className="text-xs text-gray-500">PDF files only</p>
                  </div>
                  <input
                    type="file"
                    className="hidden"
                    accept=".pdf"
                    onChange={handleFileUpload}
                    disabled={isLoading}
                  />
                </label>
              </div>
            </div>
          ) : (
            <div className="flex items-end space-x-4">
              <div className="flex-1 relative">
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Type your message..."
                  rows={1}
                  className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-xl text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                  disabled={isLoading}
                />
              </div>
              <button
                onClick={sendMessage}
                disabled={isLoading || !input.trim()}
                className="px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white rounded-xl transition-colors font-medium"
              >
                Send
              </button>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
