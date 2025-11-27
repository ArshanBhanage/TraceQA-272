"use client";

import { useState } from "react";
import Sidebar from "../components/Sidebar";
import Chatbot from "../components/Chatbot";
import TestCasesView from "../components/TestCasesView";

export default function Home() {
  const [currentPage, setCurrentPage] = useState<string>("test-cases");
  const [currentJourney, setCurrentJourney] = useState<string | null>(null);

  const handleJourneyChange = (journeyName: string | null) => {
    setCurrentJourney(journeyName);
  };

  const renderMainContent = () => {
    switch (currentPage) {
      case "test-cases":
        return <TestCasesView journeyName={currentJourney} />;
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
    <main className="flex h-screen bg-gradient-to-b from-gray-900 to-gray-950 overflow-hidden">
      {/* Sidebar */}
      <Sidebar onNavigate={setCurrentPage} currentPage={currentPage} />

      {/* Main Content Area - Takes remaining space (70%) */}
      <div className="flex-1 w-full overflow-hidden">
        {renderMainContent()}
      </div>

      {/* Chatbot - 30% of the screen width (excluding sidebar) */}
      <div className="w-[30vw] min-w-[400px] max-w-[500px] border-l border-gray-800">
        <Chatbot onJourneyChange={handleJourneyChange} />
      </div>
    </main>
  );
}
