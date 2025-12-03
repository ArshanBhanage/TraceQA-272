"use client";

import { useState } from "react";
import Sidebar from "../components/Sidebar";
import Chatbot from "../components/Chatbot";
import TestCasesView from "../components/TestCasesView";
import RAGAssistant from "../components/RAGAssistant";

export default function Home() {
  const [currentPage, setCurrentPage] = useState<string>("test-cases");
  const [currentJourney, setCurrentJourney] = useState<string | null>(null);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isChatExpanded, setIsChatExpanded] = useState(false);

  const handleJourneyChange = (journeyName: string | null) => {
    setCurrentJourney(journeyName);
  };

  const renderMainContent = () => {
    switch (currentPage) {
      case "test-cases":
        return <TestCasesView key={currentJourney || 'default'} journeyName={currentJourney} />;
      case "rag-assistant":
        return <RAGAssistant key={currentJourney || 'default'} journeyName={currentJourney} onJourneyChange={handleJourneyChange} />;
      case "journeys":
        return (
          <div className="h-full flex items-center justify-center bg-gray-950">
            <div className="text-center">
              <svg className="w-16 h-16 mx-auto text-gray-600 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
              </svg>
              <h3 className="text-xl font-semibold text-gray-300 mb-2">Journeys View</h3>
              <p className="text-gray-500">Coming soon...</p>
            </div>
          </div>
        );
      default:
        return <TestCasesView journeyName={currentJourney} />;
    }
  };

  return (
    <main className="flex flex-col h-screen bg-gradient-to-b from-gray-900 to-gray-950 overflow-hidden">
      {/* Mobile Header with Hamburger */}
      <div className="lg:hidden flex items-center justify-between p-4 border-b border-gray-800 bg-gray-900">
        <h1 className="text-xl font-bold text-white">TraceQA</h1>
        <div className="flex items-center space-x-2">
          {/* Chat Toggle for Mobile */}
          <button
            onClick={() => setIsChatExpanded(!isChatExpanded)}
            className="p-2 hover:bg-gray-800 rounded-lg text-gray-400 hover:text-white transition-colors"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
            </svg>
          </button>
          {/* Menu Toggle */}
          <button
            onClick={() => setIsMobileMenuOpen(true)}
            className="p-2 hover:bg-gray-800 rounded-lg text-gray-400 hover:text-white transition-colors"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden h-full">
        {/* Sidebar */}
        <Sidebar 
          onNavigate={setCurrentPage} 
          currentPage={currentPage}
          isMobileMenuOpen={isMobileMenuOpen}
          onCloseMobileMenu={() => setIsMobileMenuOpen(false)}
        />

        {/* Main Content Area */}
        <div className="flex-1 overflow-hidden flex flex-col lg:flex-row h-full">
          {/* Content - add bottom padding on mobile for collapsed chat bar */}
          <div className="flex-1 overflow-hidden h-full pb-[60px] lg:pb-0">
            {renderMainContent()}
          </div>

          {/* Chatbot - Desktop: Side panel, Mobile: Expandable overlay */}
          <div className={`
            lg:w-[30vw] lg:min-w-[400px] lg:max-w-[500px] lg:relative lg:h-full
            fixed inset-x-0 bottom-0 z-30 lg:z-auto
            border-t lg:border-t-0 lg:border-l border-gray-800
            bg-gray-950 lg:bg-transparent
            transition-all duration-300 ease-in-out
            flex flex-col
            ${
              isChatExpanded 
                ? 'h-[85vh] max-h-[calc(100vh-60px)]' 
                : 'h-[60px]'
            }
            lg:h-full lg:max-h-full
          `}>
            {/* Mobile Chat Header */}
            <button
              onClick={() => setIsChatExpanded(!isChatExpanded)}
              className="w-full p-4 flex items-center justify-between bg-gray-900 border-b border-gray-800 lg:hidden flex-shrink-0"
            >
              <span className="text-white font-semibold">Chat Assistant</span>
              <svg 
                className={`w-5 h-5 text-gray-400 transition-transform ${
                  isChatExpanded ? 'rotate-180' : ''
                }`} 
                fill="none" 
                stroke="currentColor" 
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
              </svg>
            </button>
            
            {/* Chat Content - takes remaining height */}
            <div className={`flex-1 overflow-hidden ${isChatExpanded ? 'block' : 'hidden lg:block'}`}>
              <Chatbot onJourneyChange={handleJourneyChange} />
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
