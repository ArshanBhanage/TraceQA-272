"use client";

import { useState, useEffect } from "react";
import * as XLSX from 'xlsx';

interface TestCase {
  id: string;
  title: string;
  description: string;
  preconditions: string[];
  steps: string[];
  expected_result: string;
  priority: string;
  status?: string;
  category?: string;
  source_document?: string;
  source_chunk?: number;
}

interface TestCasesViewProps {
  journeyName: string | null;
}

export default function TestCasesView({ journeyName }: TestCasesViewProps) {
  const [testCases, setTestCases] = useState<TestCase[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedTestCase, setSelectedTestCase] = useState<TestCase | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [availableJourneys, setAvailableJourneys] = useState<string[]>([]);
  const [selectedJourney, setSelectedJourney] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<"cards" | "table">("cards");

  useEffect(() => {
    // Load available journeys on mount
    loadAvailableJourneys();
  }, []);

  useEffect(() => {
    // Reload journeys when journeyName from props changes (new document processed)
    if (journeyName) {
      loadAvailableJourneys();
    }
  }, [journeyName]);

  useEffect(() => {
    // Use journeyName from props if available, otherwise use selected journey
    const activeJourney = journeyName || selectedJourney;
    if (activeJourney) {
      loadTestCases(activeJourney);
    }
  }, [journeyName, selectedJourney]);

  const loadAvailableJourneys = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/journeys');
      
      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          // Extract journey names from the response
          const journeyNames = data.journeys.map((j: any) => j.name);
          setAvailableJourneys(journeyNames);
          
          // Auto-select first journey if no journey is selected
          if (!journeyName && !selectedJourney && journeyNames.length > 0) {
            setSelectedJourney(journeyNames[0]);
          }
        }
      } else {
        console.error("Failed to load journeys");
      }
    } catch (error) {
      console.error("Error loading journeys:", error);
    }
  };

  const loadTestCases = async (journey: string) => {
    if (!journey) return;
    
    setIsLoading(true);
    try {
      const response = await fetch(`http://localhost:8000/api/test-cases/${journey}`);
      
      if (response.ok) {
        const data = await response.json();
        setTestCases(data.test_cases || []);
      } else {
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

  const exportToExcel = () => {
    const activeJourney = journeyName || selectedJourney;
    
    // Prepare data for Excel
    const excelData = filteredTestCases.map((tc, index) => ({
      'No.': index + 1,
      'ID': tc.id,
      'Title': tc.title,
      'Description': tc.description,
      'Preconditions': tc.preconditions.join('; '),
      'Steps': tc.steps.join('; '),
      'Expected Result': tc.expected_result,
      'Priority': tc.priority,
      'Category': tc.category || 'N/A',
      'Status': tc.status || 'Not Run'
    }));

    // Create workbook and worksheet
    const wb = XLSX.utils.book_new();
    const ws = XLSX.utils.json_to_sheet(excelData);

    // Set column widths
    const columnWidths = [
      { wch: 5 },  // No.
      { wch: 10 }, // ID
      { wch: 40 }, // Title
      { wch: 50 }, // Description
      { wch: 40 }, // Preconditions
      { wch: 50 }, // Steps
      { wch: 40 }, // Expected Result
      { wch: 10 }, // Priority
      { wch: 12 }, // Category
      { wch: 10 }  // Status
    ];
    ws['!cols'] = columnWidths;

    // Add worksheet to workbook
    XLSX.utils.book_append_sheet(wb, ws, 'Test Cases');

    // Generate filename
    const filename = `${activeJourney || 'TestCases'}_${new Date().toISOString().split('T')[0]}.xlsx`;

    // Save file
    XLSX.writeFile(wb, filename);
  };

  return (
    <div className="h-full flex flex-col bg-gray-950">
      {/* Header */}
      <div className="border-b border-gray-800 bg-gray-900/50 backdrop-blur-sm p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex-1">
            <h2 className="text-2xl font-bold text-white">Test Cases</h2>
            <div className="flex items-center space-x-4 mt-2">
              <select
                value={selectedJourney || journeyName || ""}
                onChange={(e) => setSelectedJourney(e.target.value)}
                className="px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">Select Journey...</option>
                {availableJourneys.map((journey) => (
                  <option key={journey} value={journey}>
                    {journey}
                  </option>
                ))}
              </select>
              {(selectedJourney || journeyName) && (
                <span className="text-gray-400 text-sm">
                  {testCases.length} test case{testCases.length !== 1 ? 's' : ''}
                </span>
              )}
            </div>
          </div>
          <div className="flex items-center space-x-2">
            {/* View Mode Toggle */}
            <div className="flex bg-gray-800 rounded-lg p-1">
              <button
                onClick={() => setViewMode("cards")}
                className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  viewMode === "cards"
                    ? "bg-blue-600 text-white"
                    : "text-gray-400 hover:text-white"
                }`}
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
                </svg>
              </button>
              <button
                onClick={() => setViewMode("table")}
                className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  viewMode === "table"
                    ? "bg-blue-600 text-white"
                    : "text-gray-400 hover:text-white"
                }`}
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
              </button>
            </div>

            {/* Export Button */}
            <button
              onClick={exportToExcel}
              disabled={testCases.length === 0}
              className="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white rounded-lg transition-colors text-sm font-medium flex items-center space-x-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <span>Export Excel</span>
            </button>

            {/* Refresh Button */}
            <button
              onClick={() => {
                const activeJourney = journeyName || selectedJourney;
                if (activeJourney) loadTestCases(activeJourney);
              }}
              disabled={isLoading || (!journeyName && !selectedJourney)}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white rounded-lg transition-colors text-sm font-medium flex items-center space-x-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              <span>Refresh</span>
            </button>
          </div>
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
        ) : !journeyName && !selectedJourney ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center max-w-md">
              <svg className="w-16 h-16 mx-auto text-gray-600 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
              <h3 className="text-xl font-semibold text-gray-300 mb-2">No Journey Selected</h3>
              <p className="text-gray-500">Please select a journey from the dropdown above to view test cases.</p>
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
        ) : viewMode === "cards" ? (
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
                      testCase.priority === 'high' ? 'bg-red-500/20 text-red-400' :
                      testCase.priority === 'medium' ? 'bg-yellow-500/20 text-yellow-400' :
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
                    {testCase.category && (
                      <span className="px-2 py-0.5 rounded bg-blue-500/20 text-blue-400 capitalize">
                        {testCase.category}
                      </span>
                    )}
                    <span className={`px-2 py-0.5 rounded ${
                      testCase.status === 'Passed' ? 'bg-green-500/20 text-green-400' :
                      testCase.status === 'Failed' ? 'bg-red-500/20 text-red-400' :
                      'bg-gray-500/20 text-gray-400'
                    }`}>
                      {testCase.status || 'Not Run'}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="h-full overflow-auto">
            <table className="w-full text-sm text-left">
              <thead className="text-xs text-gray-400 uppercase bg-gray-900 sticky top-0">
                <tr>
                  <th className="px-4 py-3 w-12">#</th>
                  <th className="px-4 py-3 w-24">ID</th>
                  <th className="px-4 py-3">Title</th>
                  <th className="px-4 py-3">Description</th>
                  <th className="px-4 py-3 w-20">Priority</th>
                  <th className="px-4 py-3 w-24">Category</th>
                  <th className="px-4 py-3 w-20">Steps</th>
                  <th className="px-4 py-3 w-24">Status</th>
                  <th className="px-4 py-3 w-20">Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredTestCases.map((testCase, index) => (
                  <tr
                    key={testCase.id}
                    className="border-b border-gray-800 hover:bg-gray-900/50 transition-colors"
                  >
                    <td className="px-4 py-3 text-gray-400">{index + 1}</td>
                    <td className="px-4 py-3 text-gray-300 font-mono text-xs">{testCase.id}</td>
                    <td className="px-4 py-3 text-white font-medium">{testCase.title}</td>
                    <td className="px-4 py-3 text-gray-400">
                      <div className="line-clamp-2">{testCase.description}</div>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        testCase.priority === 'high' ? 'bg-red-500/20 text-red-400' :
                        testCase.priority === 'medium' ? 'bg-yellow-500/20 text-yellow-400' :
                        'bg-green-500/20 text-green-400'
                      }`}>
                        {testCase.priority}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="px-2 py-1 rounded bg-blue-500/20 text-blue-400 text-xs capitalize">
                        {testCase.category || 'N/A'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-300 text-center">{testCase.steps.length}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${
                        testCase.status === 'Passed' ? 'bg-green-500/20 text-green-400' :
                        testCase.status === 'Failed' ? 'bg-red-500/20 text-red-400' :
                        'bg-gray-500/20 text-gray-400'
                      }`}>
                        {testCase.status || 'Not Run'}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => setSelectedTestCase(testCase)}
                        className="text-blue-400 hover:text-blue-300 transition-colors"
                      >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                        </svg>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
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
