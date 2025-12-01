"use client";

import { useState, useEffect, useRef } from "react";

// Utility function to strip markdown formatting
const stripMarkdown = (text: string): string => {
  return text
    .replace(/\*\*(.+?)\*\*/g, '$1')  // Remove bold **text**
    .replace(/\*(.+?)\*/g, '$1')       // Remove italic *text*
    .replace(/\[(.+?)\]\(.+?\)/g, '$1') // Remove links [text](url)
    .replace(/#{1,6}\s/g, '')          // Remove headers #
    .replace(/`{1,3}(.+?)`{1,3}/g, '$1') // Remove code blocks
    .replace(/~~(.+?)~~/g, '$1')       // Remove strikethrough ~~text~~
    .replace(/_{1,2}(.+?)_{1,2}/g, '$1'); // Remove underscores __text__
};

interface Message {
  role: "user" | "assistant";
  content: string;
  processingStatus?: {
    jobId: string;
    stage: string;
    status: string;
    message: string;
  };
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
  const [processingJobId, setProcessingJobId] = useState<string | null>(null);
  const [processingStage, setProcessingStage] = useState<string>("");
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    // Cleanup polling on unmount
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    // Get initial message from backend
    const getInitialMessage = async () => {
      setIsLoading(true);
      try {
        console.log('Fetching initial message from:', `/api/chat`);
        const response = await fetch(`/api/chat`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ message: "", session_id: sessionId }),
        });

        console.log('Response status:', response.status);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        console.log('Initial message data:', data);
        
        const initialMessage: Message = {
          role: "assistant",
          content: stripMarkdown(data.response),
        };
        setMessages([initialMessage]);
        
        updateChatState(data);
      } catch (error) {
        console.error("Error loading initial message:", error);
        const errorMessage: Message = {
          role: "assistant",
          content: "Sorry, there was an error connecting to the server. Please check if the backend is running.",
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
      const response = await fetch(`/api/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message: input, session_id: sessionId }),
      });

      const data = await response.json();
      const assistantMessage: Message = {
        role: "assistant",
        content: stripMarkdown(data.response),
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

      const response = await fetch(`/api/upload`, {
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
          content: data.message || "✅ Got your file. Document is being parsed now.",
          processingStatus: {
            jobId: data.job_id,
            stage: "parsing",
            status: "processing",
            message: "Parsing document..."
          }
        };
        setMessages((prev) => [...prev, uploadMessage]);
        
        // Update chat state to move away from upload step
        setChatState(prev => ({
          ...prev,
          conversationStep: "document_uploaded"
        }));
        
        const jobId = data.job_id;
        if (jobId) {
          setProcessingJobId(jobId);
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
        const response = await fetch(`/api/processing-status/${jobId}`);
        const data = await response.json();

        // Update the processing message with current status
        setMessages((prev) => {
          const lastMessage = prev[prev.length - 1];
          if (lastMessage.processingStatus?.jobId === jobId) {
            return [
              ...prev.slice(0, -1),
              {
                ...lastMessage,
                processingStatus: {
                  jobId: jobId,
                  stage: data.stage || 'processing',
                  status: data.status || 'processing',
                  message: data.message || 'Processing...'
                }
              }
            ];
          }
          return prev;
        });

        setProcessingStage(data.stage || 'processing');

        if (data.status === 'completed') {
          // Clear polling
          if (pollingIntervalRef.current) {
            clearInterval(pollingIntervalRef.current);
            pollingIntervalRef.current = null;
          }
          
          setProcessingJobId(null);
          setProcessingStage('');
          
          // Update chat state to allow normal conversation
          setChatState(prev => ({
            ...prev,
            conversationStep: "conversation"
          }));
          
          // Update final message
          setMessages((prev) => {
            const lastMessage = prev[prev.length - 1];
            if (lastMessage.processingStatus?.jobId === jobId) {
              return [
                ...prev.slice(0, -1),
                {
                  role: "assistant",
                  content: data.message || "Document parsed successfully! You can now generate test cases from the Test Cases view."
                }
              ];
            }
            return prev;
          });
        } else if (data.status === 'failed') {
          // Clear polling
          if (pollingIntervalRef.current) {
            clearInterval(pollingIntervalRef.current);
            pollingIntervalRef.current = null;
          }
          
          setProcessingJobId(null);
          setProcessingStage('');
          
          // Update chat state to allow retry
          setChatState(prev => ({
            ...prev,
            conversationStep: "conversation"
          }));
          
          setMessages((prev) => {
            const lastMessage = prev[prev.length - 1];
            if (lastMessage.processingStatus?.jobId === jobId) {
              return [
                ...prev.slice(0, -1),
                {
                  role: "assistant",
                  content: data.message || "Error processing document."
                }
              ];
            }
            return prev;
          });
        } else {
          attempts++;
          if (attempts >= maxAttempts) {
            if (pollingIntervalRef.current) {
              clearInterval(pollingIntervalRef.current);
              pollingIntervalRef.current = null;
            }
            setProcessingJobId(null);
          }
        }
      } catch (error) {
        console.error("Error polling status:", error);
        attempts++;
        if (attempts >= maxAttempts && pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
          setProcessingJobId(null);
        }
      }
    };

    // Initial poll
    poll();
    
    // Set up interval for subsequent polls
    pollingIntervalRef.current = setInterval(poll, 2000);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const startNewChat = async () => {
    // Clear any ongoing polling
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
    
    // Reset all processing state
    setProcessingJobId(null);
    setProcessingStage("");
    setSelectedFile(null);
    
    setIsLoading(true);
    try {
      await fetch(`/api/reset`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ session_id: sessionId }),
      });
      
      const response = await fetch(`/api/chat`, {
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
    <div className="h-full flex flex-col bg-gray-950 overflow-hidden">
      {/* Header - Hidden on mobile as it's shown in parent */}
      <div className="hidden lg:flex border-b border-gray-800 bg-gray-900/50 backdrop-blur-sm p-4 items-center justify-between flex-shrink-0">
        <h2 className="text-lg font-semibold text-white">Chat Assistant</h2>
        <button
          onClick={startNewChat}
          className="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-gray-200 rounded-lg transition-colors text-xs font-medium"
        >
          New Chat
        </button>
      </div>

      {/* Mobile New Chat Button */}
      <div className="lg:hidden flex justify-end p-2 border-b border-gray-800 bg-gray-900/50 flex-shrink-0">
        <button
          onClick={startNewChat}
          className="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-gray-200 rounded-lg transition-colors text-xs font-medium"
        >
          New Chat
        </button>
      </div>

      {/* Messages - Scrollable area with fixed height */}
      <div className="flex-1 overflow-y-auto p-3 md:p-4 space-y-3 md:space-y-4 min-h-0">{messages.map((message, index) => (
          <div
            key={index}
            className={`flex ${
              message.role === "user" ? "justify-end" : "justify-start"
            }`}
          >
            <div
              className={`max-w-[90%] md:max-w-[85%] rounded-lg px-3 md:px-4 py-2 ${
                message.role === "user"
                  ? "bg-blue-600 text-white"
                  : "bg-gray-800 text-gray-100 border border-gray-700"
              }`}
            >
              <p className="text-xs md:text-sm whitespace-pre-wrap">{message.content}</p>
              
              {/* Processing Progress Indicator */}
              {message.processingStatus && (
                <div className="mt-3 pt-3 border-t border-gray-700">
                  <div className="flex items-center space-x-3">
                    {/* Parsing Stage */}
                    <div className="flex flex-col items-center">
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center transition-all ${
                        message.processingStatus.stage === 'parsing' && message.processingStatus.status === 'processing'
                          ? 'bg-blue-600 animate-pulse'
                          : message.processingStatus.stage === 'parsed' || message.processingStatus.status === 'completed'
                          ? 'bg-green-600'
                          : 'bg-gray-600'
                      }`}>
                        {message.processingStatus.stage === 'parsed' || message.processingStatus.status === 'completed' ? (
                          <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                          </svg>
                        ) : (
                          <span className="text-xs text-white font-bold">1</span>
                        )}
                      </div>
                      <span className="text-xs mt-1 text-gray-400">Parsing</span>
                    </div>

                    {/* Connector Line */}
                    <div className={`h-0.5 w-12 ${
                      message.processingStatus.stage === 'parsed' || message.processingStatus.status === 'completed'
                        ? 'bg-green-600'
                        : 'bg-gray-600'
                    }`}></div>

                    {/* Parsed Stage */}
                    <div className="flex flex-col items-center">
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center transition-all ${
                        message.processingStatus.stage === 'parsed' && message.processingStatus.status === 'processing'
                          ? 'bg-blue-600 animate-pulse'
                          : message.processingStatus.status === 'completed'
                          ? 'bg-green-600'
                          : 'bg-gray-600'
                      }`}>
                        {message.processingStatus.status === 'completed' ? (
                          <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                          </svg>
                        ) : (
                          <span className="text-xs text-white font-bold">2</span>
                        )}
                      </div>
                      <span className="text-xs mt-1 text-gray-400">Parsed</span>
                    </div>

                    {/* Connector Line */}
                    <div className={`h-0.5 w-12 ${
                      message.processingStatus.status === 'completed'
                        ? 'bg-green-600'
                        : 'bg-gray-600'
                    }`}></div>

                    {/* Ready Stage */}
                    <div className="flex flex-col items-center">
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center transition-all ${
                        message.processingStatus.status === 'completed'
                          ? 'bg-green-600'
                          : 'bg-gray-600'
                      }`}>
                        {message.processingStatus.status === 'completed' ? (
                          <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                          </svg>
                        ) : (
                          <span className="text-xs text-white font-bold">3</span>
                        )}
                      </div>
                      <span className="text-xs mt-1 text-gray-400">Ready</span>
                    </div>
                  </div>
                  <p className="text-xs text-gray-400 mt-3">{message.processingStatus.message}</p>
                </div>
              )}
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

      {/* Input Area - Fixed at bottom */}
      <div className="border-t border-gray-800 bg-gray-900/50 p-2 md:p-4 flex-shrink-0">
        {chatState.conversationStep === "awaiting_document_upload" ? (
          <div className="space-y-2">
            <label className="flex flex-col items-center justify-center w-full h-20 md:h-24 border-2 border-gray-700 border-dashed rounded-lg cursor-pointer bg-gray-800 hover:bg-gray-750 transition-colors">
              <div className="flex flex-col items-center justify-center py-2">
                <svg
                  className="w-6 md:w-8 h-6 md:h-8 mb-1 md:mb-2 text-gray-400"
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
          <div className="flex items-end space-x-1 md:space-x-2">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Type your message..."
              rows={2}
              className="flex-1 px-2 md:px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none text-xs md:text-sm"
              disabled={isLoading}
            />
            <button
              onClick={sendMessage}
              disabled={isLoading || !input.trim()}
              className="px-3 md:px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white rounded-lg transition-colors font-medium text-xs md:text-sm"
            >
              Send
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
