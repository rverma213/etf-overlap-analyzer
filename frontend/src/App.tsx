import { useState, useEffect } from 'react';
import { fetchETFs, analyzeOverlap } from './api';
import type { ETFInfo, OverlapResult } from './types';

function App() {
  const [etfs, setEtfs] = useState<ETFInfo[]>([]);
  const [etf1, setEtf1] = useState<string>('');
  const [etf2, setEtf2] = useState<string>('');
  const [result, setResult] = useState<OverlapResult | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [loadingEtfs, setLoadingEtfs] = useState<boolean>(true);

  useEffect(() => {
    fetchETFs()
      .then((data) => {
        setEtfs(data);
        setLoadingEtfs(false);
      })
      .catch((err) => {
        setError('Failed to load ETFs: ' + err.message);
        setLoadingEtfs(false);
      });
  }, []);

  const handleAnalyze = async () => {
    if (!etf1 || !etf2) {
      setError('Please select two ETFs to compare');
      return;
    }

    if (etf1 === etf2) {
      setError('Please select two different ETFs');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const data = await analyzeOverlap(etf1, etf2);
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 py-12">
        <header className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            ETF Overlap Analyzer
          </h1>
          <p className="text-gray-600">
            Compare holdings between ETFs using SEC EDGAR data
          </p>
        </header>

        <div className="bg-white rounded-lg shadow-md p-6 mb-8">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div>
              <label
                htmlFor="etf1"
                className="block text-sm font-medium text-gray-700 mb-2"
              >
                First ETF
              </label>
              <select
                id="etf1"
                value={etf1}
                onChange={(e) => setEtf1(e.target.value)}
                disabled={loadingEtfs}
                className="w-full px-4 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
              >
                <option value="">Select an ETF</option>
                {etfs.map((etf) => (
                  <option key={etf.ticker} value={etf.ticker}>
                    {etf.ticker} - {etf.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label
                htmlFor="etf2"
                className="block text-sm font-medium text-gray-700 mb-2"
              >
                Second ETF
              </label>
              <select
                id="etf2"
                value={etf2}
                onChange={(e) => setEtf2(e.target.value)}
                disabled={loadingEtfs}
                className="w-full px-4 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
              >
                <option value="">Select an ETF</option>
                {etfs.map((etf) => (
                  <option key={etf.ticker} value={etf.ticker}>
                    {etf.ticker} - {etf.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <button
            onClick={handleAnalyze}
            disabled={loading || loadingEtfs || !etf1 || !etf2}
            className="w-full bg-blue-600 text-white py-3 px-6 rounded-md font-medium hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? 'Analyzing...' : 'Analyze Overlap'}
          </button>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md mb-8">
            {error}
          </div>
        )}

        {loading && (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-blue-600 border-t-transparent"></div>
            <p className="mt-4 text-gray-600">
              Fetching holdings data from SEC EDGAR...
            </p>
          </div>
        )}

        {result && (
          <div className="bg-white rounded-lg shadow-md overflow-hidden">
            <div className="bg-blue-600 text-white px-6 py-8 text-center">
              <p className="text-sm uppercase tracking-wide mb-2">
                Overlap Percentage
              </p>
              <p className="text-6xl font-bold">{result.overlap_percentage}%</p>
              <p className="mt-4 text-blue-100">
                {result.common_holdings_count} common holdings out of{' '}
                {result.etf1_total_holdings} ({result.etf1_ticker}) and{' '}
                {result.etf2_total_holdings} ({result.etf2_ticker})
              </p>
            </div>

            <div className="p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">
                Top Overlapping Holdings
              </h2>

              {result.top_overlapping.length === 0 ? (
                <p className="text-gray-500 text-center py-8">
                  No overlapping holdings found
                </p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-gray-200">
                        <th className="text-left py-3 px-4 font-medium text-gray-600">
                          Holding
                        </th>
                        <th className="text-right py-3 px-4 font-medium text-gray-600">
                          {result.etf1_ticker} Weight
                        </th>
                        <th className="text-right py-3 px-4 font-medium text-gray-600">
                          {result.etf2_ticker} Weight
                        </th>
                        <th className="text-right py-3 px-4 font-medium text-gray-600">
                          Overlap
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.top_overlapping.map((holding, index) => (
                        <tr
                          key={holding.cusip || index}
                          className="border-b border-gray-100 hover:bg-gray-50"
                        >
                          <td className="py-3 px-4">
                            <span className="font-medium text-gray-900">
                              {holding.name}
                            </span>
                            {holding.cusip && (
                              <span className="block text-xs text-gray-500">
                                CUSIP: {holding.cusip}
                              </span>
                            )}
                          </td>
                          <td className="text-right py-3 px-4 text-gray-700">
                            {holding.weight_etf1.toFixed(2)}%
                          </td>
                          <td className="text-right py-3 px-4 text-gray-700">
                            {holding.weight_etf2.toFixed(2)}%
                          </td>
                          <td className="text-right py-3 px-4 font-medium text-blue-600">
                            {holding.overlap_contribution.toFixed(2)}%
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}

        <footer className="text-center mt-12 text-gray-500 text-sm">
          Data sourced from SEC EDGAR N-PORT filings
        </footer>
      </div>
    </div>
  );
}

export default App;
