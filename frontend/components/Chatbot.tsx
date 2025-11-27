"use client";

import { useState, useEffect, useRef } from "react";

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface ChatState {
  conversationStep: string;
  journeyName: string | null;
  documentType: string | null;
}

interface ChatbotProps {
  onJourneyChange?: (journeyName: string | null) => void;
}

export default function Chatbot({ onJourneyChange }: ChatbotProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [chatState, setChatState] = useState<ChatState>({
    conversationStep: "initial",
    journeyName: null,
    documentType: null,
  });
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const sessionId = "user-session-1";

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

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
        
        updateChatState(data);
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

  const updateChatState = (data: any) => {
    const newState = {
      conversationStep: data.conversation_step,
      journeyName: data.journey_name,
      documentType: data.document_type,
    };
    setChatState(newState);
    
    // Notify parent component of journey change
    if (onJourneyChange && data.journey_name !== chatState.journeyName) {
      onJourneyChange(data.journey_name);
    }
  };

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
      
      updateChatState(data);
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
      
      setIsLoading(false);
      setSelectedFile(null);
      e.target.value = '';
      
      if (data.error) {
        const errorMessage: Message = {
          role: "assistant",
          content: data.error,
        };
        setMessages((prev) => [...prev, errorMessage]);
      } else {
        const uploadMessage: Message = {
          role: "assistant",
          content: data.message || "✅ Got your file. I'm processing it now — this can take a few minutes. I'll send the results as soon as they're ready.",
        };
        setMessages((prev) => [...prev, uploadMessage]);
        
        const jobId = data.job_id;
        if (jobId) {
          pollProcessingStatus(jobId);
        }
      }
    } catch (error) {
      console.error("Error:", error);
      const errorMessage: Message = {
        role: "assistant",
        content: "Sorry, there was an error uploading your document.",
      };
      setMessages((prev) => [...prev, errorMessage]);
      setIsLoading(false);
      setSelectedFile(null);
      e.target.value = '';
    }
  };

  const pollProcessingStatus = async (jobId: string) => {
    const maxAttempts = 60;
    let attempts = 0;

    const poll = async () => {
      try {
        const response = await fetch(`http://localhost:8000/api/processing-status/${jobId}`);
        const data = await response.json();

        if (data.status === 'completed') {
          const completionMessage: Message = {
            role: "assistant",
            content: data.message,
          };
          setMessages((prev) => [...prev, completionMessage]);
          
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
            
            updateChatState(chatData);
          } catch (err) {
            console.error("Error getting next step:", err);
          }
        } else if (data.status === 'failed') {
          const errorMessage: Message = {
            role: "assistant",
            content: data.message || "Processing failed. Please try again.",
          };
          setMessages((prev) => [...prev, errorMessage]);
        } else if (data.status === 'processing' && attempts < maxAttempts) {
          attempts++;
          setTimeout(poll, 5000);
        } else if (attempts >= maxAttempts) {
          const timeoutMessage: Message = {
            role: "assistant",
            content: "⏱️ Processing is taking longer than expected. Please check back later or try uploading the document again.",
          };
          setMessages((prev) => [...prev, timeoutMessage]);
        }
      } catch (error) {
        console.error("Error polling status:", error);
      }
    };

    setTimeout(poll, 3000);
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
      await fetch("http://localhost:8000/api/reset", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(sessionId),
      });
      
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
      updateChatState(data);
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
    <div className="h-full flex flex-col bg-gray-950 border-l border-gray-800">
      {/* Header */}
      <div className="border-b border-gray-800 bg-gray-900/50 backdrop-blur-sm p-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-white">Chat Assistant</h2>
        <button
          onClick={startNewChat}
          className="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-gray-200 rounded-lg transition-colors text-xs font-medium"
        >
          New Chat
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message, index) => (
          <div
            key={index}
            className={`flex ${
              message.role === "user" ? "justify-end" : "justify-start"
            }`}
          >
            <div
              className={`max-w-[85%] rounded-lg px-4 py-2 ${
                message.role === "user"
                  ? "bg-blue-600 text-white"
                  : "bg-gray-800 text-gray-100 border border-gray-700"
              }`}
            >
              <p className="text-sm whitespace-pre-wrap">{message.content}</p>
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-800 border border-gray-700 rounded-lg px-4 py-2">
              <div className="flex space-x-1">
                <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce delay-100"></div>
                <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce delay-200"></div>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="border-t border-gray-800 bg-gray-900/50 p-4">
        {chatState.conversationStep === "awaiting_document_upload" ? (
          <div className="space-y-2">
            <label className="flex flex-col items-center justify-center w-full h-24 border-2 border-gray-700 border-dashed rounded-lg cursor-pointer bg-gray-800 hover:bg-gray-750 transition-colors">
              <div className="flex flex-col items-center justify-center py-2">
                <svg
                  className="w-8 h-8 mb-2 text-gray-400"
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
                <p className="text-xs text-gray-400">
                  <span className="font-semibold">Upload PDF</span>
                </p>
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
        ) : (
          <div className="flex items-end space-x-2">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Type your message..."
              rows={2}
              className="flex-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none text-sm"
              disabled={isLoading}
            />
            <button
              onClick={sendMessage}
              disabled={isLoading || !input.trim()}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white rounded-lg transition-colors font-medium text-sm"
            >
              Send
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
