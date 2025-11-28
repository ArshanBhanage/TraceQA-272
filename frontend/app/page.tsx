"use client";

import { useState } from "react";
import Sidebar from "../components/Sidebar";
import Chatbot from "../components/Chatbot";
import TestCasesView from "../components/TestCasesView";
import RAGAssistant from "../components/RAGAssistant";

export default function Home() {
  const [currentPage, setCurrentPage] = useState<string>("test-cases");
  const [currentJourney, setCurrentJourney] = useState<string | null>(null);

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
    <main className="flex flex-col lg:flex-row h-screen bg-gradient-to-b from-gray-900 to-gray-950 overflow-hidden">
      {/* Sidebar */}
      <Sidebar onNavigate={setCurrentPage} currentPage={currentPage} />

      {/* Main Content Area - Responsive width */}
      <div className="flex-1 w-full lg:w-auto overflow-hidden order-2 lg:order-1">
        {renderMainContent()}
      </div>

      {/* Chatbot - Responsive width and positioning */}
      <div className="w-full lg:w-[30vw] lg:min-w-[400px] lg:max-w-[500px] h-[40vh] lg:h-auto border-t lg:border-t-0 lg:border-l border-gray-800 order-3 lg:order-2">
        <Chatbot onJourneyChange={handleJourneyChange} />
      </div>
    </main>
  );
}
