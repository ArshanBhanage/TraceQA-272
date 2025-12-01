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

interface Evidence {
  document: string;
  journey: string;
  chunk_index: number;
  score: number;
  text: string;
}

interface Message {
  role: "user" | "assistant";
  content: string;
  evidence?: Evidence[];
  sourcesCount?: number;
}

interface RAGAssistantProps {
  journeyName: string | null;
  onJourneyChange?: (journeyName: string | null) => void;
}

export default function RAGAssistant({ journeyName, onJourneyChange }: RAGAssistantProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [stats, setStats] = useState<any>(null);
  const [selectedEvidence, setSelectedEvidence] = useState<Evidence | null>(null);
  const [availableJourneys, setAvailableJourneys] = useState<string[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    loadStats();
    loadAvailableJourneys();
  }, []);

  useEffect(() => {
    // Add welcome message when component mounts or journey changes
    if (!journeyName) {
      setMessages([{
        role: "assistant",
        content: stripMarkdown(`Hello! I'm your RAG (Retrieval-Augmented Generation) Assistant.

⚠️ **Please select a journey from the dropdown above!**

Once you select a journey, you can ask questions about the documents in that journey, and I'll provide evidence-based answers with source citations.`)
      }]);
    } else {
      setMessages([{
        role: "assistant",
        content: stripMarkdown(`Hello! I'm your RAG (Retrieval-Augmented Generation) Assistant.

✅ **Currently searching in journey: "${journeyName}"**

Ask me anything about the documents in this journey, and I'll provide evidence-based answers with source citations.`)
      }]);
    }
  }, [journeyName]);

  const loadStats = async () => {
    try {
      const response = await fetch("/api/rag/stats");
      const data = await response.json();
      if (data.success) {
        setStats(data);
      }
    } catch (error) {
      console.error("Failed to load RAG stats:", error);
    }
  };

  const loadAvailableJourneys = async () => {
    try {
      const response = await fetch("/api/journeys");
      const data = await response.json();
      if (data.journeys && Array.isArray(data.journeys)) {
        // Extract just the journey names from the journey objects
        const journeyNames = data.journeys.map((j: any) => j.name);
        setAvailableJourneys(journeyNames);
      }
    } catch (error) {
      console.error("Failed to load journeys:", error);
    }
  };

  const askQuestion = async () => {
    if (!input.trim()) return;

    const userMessage: Message = { role: "user", content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const response = await fetch(`/api/rag/query`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: input,
          journey_name: journeyName,
          top_k: 5
        })
      });

      const data = await response.json();
      
      const assistantMessage: Message = {
        role: "assistant",
        content: stripMarkdown(data.answer),
        evidence: data.evidence || [],
        sourcesCount: data.sources_count || 0
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error("Error:", error);
      const errorMessage: Message = {
        role: "assistant",
        content: "Sorry, there was an error processing your question."
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      askQuestion();
    }
  };

  return (
    <div className="h-full flex flex-col bg-gray-950">
      {/* Header */}
      <div className="border-b border-gray-800 bg-gray-900/50 backdrop-blur-sm p-4">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center space-x-2">
            <svg className="w-6 h-6 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
            <h2 className="text-lg font-semibold text-white">RAG Assistant</h2>
          </div>
          
          {/* Journey Selector Dropdown */}
          {onJourneyChange && (
            <select
              value={journeyName || ""}
              onChange={(e) => onJourneyChange(e.target.value || null)}
              className="px-3 py-1.5 text-sm bg-gray-800 border border-gray-700 rounded-lg text-gray-300 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent hover:bg-gray-750 transition-colors"
            >
              <option value="">Select Journey...</option>
              {availableJourneys.map((journey) => (
                <option key={journey} value={journey}>
                  📁 {journey}
                </option>
              ))}
            </select>
          )}
        </div>
        
        {/* Stats */}
        {stats && (
          <div className="flex items-center space-x-4 text-xs">
            <span className="text-gray-400">
              📊 {stats.total_vectors || 0} vectors indexed
            </span>
            {journeyName && (
              <span className="px-2 py-1 bg-purple-900/30 text-purple-300 rounded">
                Journey: {journeyName}
              </span>
            )}
          </div>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message, index) => (
          <div
            key={index}
            className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[85%] rounded-lg px-4 py-3 ${
                message.role === "user"
                  ? "bg-purple-600 text-white"
                  : "bg-gray-800 text-gray-100 border border-gray-700"
              }`}
            >
              <p className="text-sm whitespace-pre-wrap">{message.content}</p>
              
              {/* Evidence Section */}
              {message.evidence && message.evidence.length > 0 && (
                <div className="mt-4 pt-3 border-t border-gray-700">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-semibold text-purple-400">
                      📚 {message.sourcesCount} Source{message.sourcesCount !== 1 ? 's' : ''}
                    </span>
                  </div>
                  <div className="space-y-2">
                    {message.evidence.map((evidence, idx) => (
                      <div
                        key={idx}
                        onClick={() => setSelectedEvidence(evidence)}
                        className="p-2 bg-gray-900/50 rounded border border-gray-700 hover:border-purple-500 cursor-pointer transition-colors"
                      >
                        <div className="flex items-start justify-between mb-1">
                          <span className="text-xs font-medium text-gray-300">
                            {evidence.document}
                          </span>
                          <span className="text-xs text-green-400">
                            {evidence.score.toFixed(1)}%
                          </span>
                        </div>
                        <p className="text-xs text-gray-400 line-clamp-2">
                          {evidence.text}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}
        
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-800 border border-gray-700 rounded-lg px-4 py-3">
              <div className="flex items-center space-x-2">
                <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce delay-100"></div>
                <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce delay-200"></div>
                <span className="text-xs text-gray-400 ml-2">Searching knowledge base...</span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="border-t border-gray-800 bg-gray-900/50 p-4">
        {!journeyName ? (
          <div className="text-center py-4">
            <p className="text-gray-400 text-sm mb-2">
              ⚠️ Please select a journey from the dropdown above to start asking questions
            </p>
          </div>
        ) : (
          <div className="flex items-end space-x-2">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder={`Ask a question about journey "${journeyName}"...`}
              rows={2}
              className="flex-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none text-sm"
              disabled={isLoading}
            />
            <button
              onClick={askQuestion}
              disabled={isLoading || !input.trim()}
              className="px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white rounded-lg transition-colors font-medium text-sm"
            >
              Ask
            </button>
          </div>
        )}
      </div>

      {/* Evidence Modal */}
      {selectedEvidence && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setSelectedEvidence(null)}>
          <div className="bg-gray-900 rounded-xl border border-gray-700 max-w-2xl w-full max-h-[80vh] overflow-hidden" onClick={(e) => e.stopPropagation()}>
            <div className="p-4 border-b border-gray-800 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-white">Evidence Details</h3>
              <button
                onClick={() => setSelectedEvidence(null)}
                className="text-gray-400 hover:text-white transition-colors"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="p-6 overflow-y-auto max-h-[calc(80vh-80px)]">
              <div className="space-y-4">
                <div>
                  <label className="text-sm font-semibold text-gray-400">Document</label>
                  <p className="text-white">{selectedEvidence.document}</p>
                </div>
                <div>
                  <label className="text-sm font-semibold text-gray-400">Journey</label>
                  <p className="text-white">{selectedEvidence.journey}</p>
                </div>
                <div>
                  <label className="text-sm font-semibold text-gray-400">Relevance Score</label>
                  <p className="text-green-400 font-semibold">{selectedEvidence.score.toFixed(1)}%</p>
                </div>
                <div>
                  <label className="text-sm font-semibold text-gray-400">Content</label>
                  <p className="text-gray-300 bg-gray-800 p-4 rounded-lg whitespace-pre-wrap">{selectedEvidence.text}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
