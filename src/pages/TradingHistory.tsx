import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { 
  Filter, 
  Download, 
  Search,
  Calendar,
  TrendingUp,
  TrendingDown,
  Clock,
  DollarSign
} from 'lucide-react';

// Mock data - replace with real API calls
const mockTrades = [
  {
    id: 1,
    pair: 'BTC/USDT',
    type: 'buy',
    amount: 0.5,
    price: 47500,
    total: 23750,
    fee: 23.75,
    time: '2024-01-15 14:30:00',
    status: 'completed',
    strategy: 'SuperTrend BTC',
  },
  {
    id: 2,
    pair: 'ETH/USDT',
    type: 'sell',
    amount: 2.0,
    price: 3200,
    total: 6400,
    fee: 6.40,
    time: '2024-01-15 13:45:00',
    status: 'completed',
    strategy: 'RSI Divergence ETH',
  },
  {
    id: 3,
    pair: 'ADA/USDT',
    type: 'buy',
    amount: 1000,
    price: 0.45,
    total: 450,
    fee: 0.45,
    time: '2024-01-15 12:20:00',
    status: 'completed',
    strategy: 'Bollinger Band Scalper',
  },
  {
    id: 4,
    pair: 'BTC/USDT',
    type: 'sell',
    amount: 0.3,
    price: 47800,
    total: 14340,
    fee: 14.34,
    time: '2024-01-15 11:15:00',
    status: 'completed',
    strategy: 'SuperTrend BTC',
  },
];

const TradingHistory: React.FC = () => {
  const [trades, setTrades] = useState(mockTrades);
  const [filters, setFilters] = useState({
    pair: '',
    type: '',
    status: '',
    strategy: '',
    dateFrom: '',
    dateTo: '',
  });
  const [searchTerm, setSearchTerm] = useState('');

  const handleFilterChange = (key: string, value: string) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  const filteredTrades = trades.filter(trade => {
    const matchesSearch = trade.pair.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         trade.strategy.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesFilters = (!filters.pair || trade.pair === filters.pair) &&
                          (!filters.type || trade.type === filters.type) &&
                          (!filters.status || trade.status === filters.status) &&
                          (!filters.strategy || trade.strategy === filters.strategy);

    return matchesSearch && matchesFilters;
  });

  const exportTrades = () => {
    // Implement CSV export functionality
    console.log('Exporting trades...');
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="flex flex-col sm:flex-row sm:items-center sm:justify-between"
      >
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Trading History
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            View and analyze your trading performance over time
          </p>
        </div>
        <div className="mt-4 sm:mt-0">
          <button
            onClick={exportTrades}
            className="btn-secondary inline-flex items-center"
          >
            <Download className="h-4 w-4 mr-2" />
            Export CSV
          </button>
        </div>
      </motion.div>

      {/* Filters and Search */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.1 }}
        className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6"
      >
        <div className="flex flex-col lg:flex-row gap-4">
          {/* Search */}
          <div className="flex-1">
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Search className="h-5 w-5 text-gray-400" />
              </div>
              <input
                type="text"
                placeholder="Search trades..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="input-field pl-10"
              />
            </div>
          </div>

          {/* Filters */}
          <div className="flex flex-wrap gap-3">
            <select
              value={filters.pair}
              onChange={(e) => handleFilterChange('pair', e.target.value)}
              className="input-field max-w-xs"
            >
              <option value="">All Pairs</option>
              <option value="BTC/USDT">BTC/USDT</option>
              <option value="ETH/USDT">ETH/USDT</option>
              <option value="ADA/USDT">ADA/USDT</option>
            </select>

            <select
              value={filters.type}
              onChange={(e) => handleFilterChange('type', e.target.value)}
              className="input-field max-w-xs"
            >
              <option value="">All Types</option>
              <option value="buy">Buy</option>
              <option value="sell">Sell</option>
            </select>

            <select
              value={filters.strategy}
              onChange={(e) => handleFilterChange('strategy', e.target.value)}
              className="input-field max-w-xs"
            >
              <option value="">All Strategies</option>
              <option value="SuperTrend BTC">SuperTrend BTC</option>
              <option value="RSI Divergence ETH">RSI Divergence ETH</option>
              <option value="Bollinger Band Scalper">Bollinger Band Scalper</option>
            </select>

            <div className="flex items-center space-x-2">
              <Calendar className="h-5 w-5 text-gray-400" />
              <input
                type="date"
                value={filters.dateFrom}
                onChange={(e) => handleFilterChange('dateFrom', e.target.value)}
                className="input-field max-w-xs"
              />
              <span className="text-gray-500">to</span>
              <input
                type="date"
                value={filters.dateTo}
                onChange={(e) => handleFilterChange('dateTo', e.target.value)}
                className="input-field max-w-xs"
              />
            </div>
          </div>
        </div>
      </motion.div>

      {/* Trades Table */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.2 }}
        className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden"
      >
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white">
            Trade History ({filteredTrades.length} trades)
          </h3>
        </div>
        
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead className="bg-gray-50 dark:bg-gray-700">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Trade Details
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Amount & Price
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Total & Fees
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Strategy
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Time
                </th>
              </tr>
            </thead>
            <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
              {filteredTrades.map((trade) => (
                <tr key={trade.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <div className={`p-2 rounded-lg ${
                        trade.type === 'buy' 
                          ? 'bg-success-100 dark:bg-success-900' 
                          : 'bg-danger-100 dark:bg-danger-900'
                      }`}>
                        {trade.type === 'buy' ? (
                          <TrendingUp className="h-4 w-4 text-success-600 dark:text-success-400" />
                        ) : (
                          <TrendingDown className="h-4 w-4 text-danger-600 dark:text-danger-400" />
                        )}
                      </div>
                      <div className="ml-3">
                        <div className="text-sm font-medium text-gray-900 dark:text-white">
                          {trade.pair}
                        </div>
                        <div className="text-sm text-gray-500 dark:text-gray-400">
                          {trade.type.toUpperCase()}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900 dark:text-white">
                      {trade.amount} {trade.pair.split('/')[0]}
                    </div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">
                      @ ${trade.price.toLocaleString()}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-medium text-gray-900 dark:text-white">
                      ${trade.total.toLocaleString()}
                    </div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">
                      Fee: ${trade.fee.toFixed(2)}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900 dark:text-white">
                      {trade.strategy}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                    <div className="flex items-center">
                      <Clock className="h-4 w-4 mr-1" />
                      {trade.time}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Empty State */}
        {filteredTrades.length === 0 && (
          <div className="text-center py-12">
            <div className="mx-auto h-16 w-16 text-gray-400 dark:text-gray-600 mb-4">
              <Search className="h-16 w-16" />
            </div>
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
              No trades found
            </h3>
            <p className="text-gray-500 dark:text-gray-400">
              Try adjusting your filters or search terms
            </p>
          </div>
        )}
      </motion.div>
    </div>
  );
};

export default TradingHistory;
