"use client";

import { useState, useEffect } from "react";

interface TestCase {
  id: string;
  title: string;
  description: string;
  preconditions: string[];
  steps: string[];
  expected_result: string;
  priority: string;
  status: string;
}

interface TestCasesViewProps {
  journeyName: string | null;
}

export default function TestCasesView({ journeyName }: TestCasesViewProps) {
  const [testCases, setTestCases] = useState<TestCase[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedTestCase, setSelectedTestCase] = useState<TestCase | null>(null);
  const [searchTerm, setSearchTerm] = useState("");

  useEffect(() => {
    if (journeyName) {
      loadTestCases();
    }
  }, [journeyName]);

  const loadTestCases = async () => {
    if (!journeyName) return;
    
    setIsLoading(true);
    try {
      // TODO: Replace with actual API call to fetch test cases
      const response = await fetch(`http://localhost:8000/api/test-cases/${journeyName}`);
      
      if (response.ok) {
        const data = await response.json();
        setTestCases(data.test_cases || []);
      } else {
        // For now, load from local file if API not available
        console.log("API not available, showing placeholder data");
        setTestCases([]);
      }
    } catch (error) {
      console.error("Error loading test cases:", error);
      setTestCases([]);
    } finally {
      setIsLoading(false);
    }
  };

  const filteredTestCases = testCases.filter((tc) =>
    tc.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
    tc.description.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="h-full flex flex-col bg-gray-950">
      {/* Header */}
      <div className="border-b border-gray-800 bg-gray-900/50 backdrop-blur-sm p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-2xl font-bold text-white">Test Cases</h2>
            {journeyName && (
              <p className="text-gray-400 mt-1">Journey: {journeyName}</p>
            )}
          </div>
          <button
            onClick={loadTestCases}
            disabled={isLoading || !journeyName}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white rounded-lg transition-colors text-sm font-medium flex items-center space-x-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            <span>Refresh</span>
          </button>
        </div>

        {/* Search Bar */}
        <div className="relative">
          <svg
            className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-500"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            placeholder="Search test cases..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {isLoading ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center">
              <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mb-4"></div>
              <p className="text-gray-400">Loading test cases...</p>
            </div>
          </div>
        ) : !journeyName ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center max-w-md">
              <svg className="w-16 h-16 mx-auto text-gray-600 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
              <h3 className="text-xl font-semibold text-gray-300 mb-2">No Journey Selected</h3>
              <p className="text-gray-500">Please create or select a journey from the chat to view test cases.</p>
            </div>
          </div>
        ) : filteredTestCases.length === 0 ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center max-w-md">
              <svg className="w-16 h-16 mx-auto text-gray-600 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
              </svg>
              <h3 className="text-xl font-semibold text-gray-300 mb-2">No Test Cases Found</h3>
              <p className="text-gray-500">
                {searchTerm ? "No test cases match your search." : "Upload documents to generate test cases."}
              </p>
            </div>
          </div>
        ) : (
          <div className="h-full overflow-y-auto p-6">
            <div className="grid gap-4">
              {filteredTestCases.map((testCase) => (
                <div
                  key={testCase.id}
                  onClick={() => setSelectedTestCase(testCase)}
                  className="bg-gray-900 border border-gray-800 rounded-lg p-4 hover:border-blue-500 cursor-pointer transition-colors"
                >
                  <div className="flex items-start justify-between mb-2">
                    <h3 className="text-lg font-semibold text-white">{testCase.title}</h3>
                    <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                      testCase.priority === 'High' ? 'bg-red-500/20 text-red-400' :
                      testCase.priority === 'Medium' ? 'bg-yellow-500/20 text-yellow-400' :
                      'bg-green-500/20 text-green-400'
                    }`}>
                      {testCase.priority}
                    </span>
                  </div>
                  <p className="text-gray-400 text-sm mb-3">{testCase.description}</p>
                  <div className="flex items-center space-x-4 text-xs text-gray-500">
                    <span className="flex items-center space-x-1">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                      </svg>
                      <span>{testCase.steps.length} steps</span>
                    </span>
                    <span className={`px-2 py-0.5 rounded ${
                      testCase.status === 'Passed' ? 'bg-green-500/20 text-green-400' :
                      testCase.status === 'Failed' ? 'bg-red-500/20 text-red-400' :
                      'bg-gray-500/20 text-gray-400'
                    }`}>
                      {testCase.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Test Case Detail Modal */}
      {selectedTestCase && (
        <div
          className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50"
          onClick={() => setSelectedTestCase(null)}
        >
          <div
            className="bg-gray-900 border border-gray-800 rounded-xl max-w-3xl w-full max-h-[80vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="sticky top-0 bg-gray-900 border-b border-gray-800 p-6 flex items-start justify-between">
              <div className="flex-1">
                <h2 className="text-2xl font-bold text-white mb-2">{selectedTestCase.title}</h2>
                <p className="text-gray-400">{selectedTestCase.description}</p>
              </div>
              <button
                onClick={() => setSelectedTestCase(null)}
                className="ml-4 p-2 hover:bg-gray-800 rounded-lg text-gray-400 hover:text-white transition-colors"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="p-6 space-y-6">
              {/* Preconditions */}
              {selectedTestCase.preconditions.length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold text-white mb-3">Preconditions</h3>
                  <ul className="list-disc list-inside space-y-2">
                    {selectedTestCase.preconditions.map((condition, idx) => (
                      <li key={idx} className="text-gray-300">{condition}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Steps */}
              <div>
                <h3 className="text-lg font-semibold text-white mb-3">Test Steps</h3>
                <ol className="list-decimal list-inside space-y-2">
                  {selectedTestCase.steps.map((step, idx) => (
                    <li key={idx} className="text-gray-300">{step}</li>
                  ))}
                </ol>
              </div>

              {/* Expected Result */}
              <div>
                <h3 className="text-lg font-semibold text-white mb-3">Expected Result</h3>
                <p className="text-gray-300 bg-gray-800 p-4 rounded-lg">{selectedTestCase.expected_result}</p>
              </div>

              {/* Metadata */}
              <div className="flex items-center space-x-6 pt-4 border-t border-gray-800">
                <div>
                  <span className="text-gray-500 text-sm">Priority:</span>
                  <span className={`ml-2 px-3 py-1 rounded-full text-xs font-medium ${
                    selectedTestCase.priority === 'High' ? 'bg-red-500/20 text-red-400' :
                    selectedTestCase.priority === 'Medium' ? 'bg-yellow-500/20 text-yellow-400' :
                    'bg-green-500/20 text-green-400'
                  }`}>
                    {selectedTestCase.priority}
                  </span>
                </div>
                <div>
                  <span className="text-gray-500 text-sm">Status:</span>
                  <span className={`ml-2 px-3 py-1 rounded-full text-xs font-medium ${
                    selectedTestCase.status === 'Passed' ? 'bg-green-500/20 text-green-400' :
                    selectedTestCase.status === 'Failed' ? 'bg-red-500/20 text-red-400' :
                    'bg-gray-500/20 text-gray-400'
                  }`}>
                    {selectedTestCase.status}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
