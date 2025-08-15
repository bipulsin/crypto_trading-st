import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
  Plus, 
  Play, 
  Pause, 
  Edit, 
  Trash2, 
  Eye, 
  Settings,
  TrendingUp,
  BarChart3,
  Activity,
  Clock,
  DollarSign
} from 'lucide-react';

// Mock data - replace with real API calls
const mockStrategies = [
  {
    id: 1,
    name: 'SuperTrend BTC Strategy',
    type: 'SuperTrend',
    status: 'active',
    pair: 'BTC/USDT',
    pnl: '+$2,450.30',
    pnlPercent: '+8.5%',
    trades: 45,
    winRate: '72%',
    lastTrade: '2 hours ago',
    isActive: true,
  },
  {
    id: 2,
    name: 'RSI Divergence ETH',
    type: 'RSI',
    status: 'paused',
    pair: 'ETH/USDT',
    pnl: '-$180.50',
    pnlPercent: '-2.1%',
    trades: 23,
    winRate: '65%',
    lastTrade: '1 day ago',
    isActive: false,
  },
  {
    id: 3,
    name: 'Bollinger Band Scalper',
    type: 'Bollinger Bands',
    status: 'active',
    pair: 'ADA/USDT',
    pnl: '+$890.20',
    pnlPercent: '+15.2%',
    trades: 67,
    winRate: '78%',
    lastTrade: '30 minutes ago',
    isActive: true,
  },
];

const StrategyManagement: React.FC = () => {
  const [strategies, setStrategies] = useState(mockStrategies);
  const [selectedStrategy, setSelectedStrategy] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleToggleStrategy = async (strategyId: number) => {
    setIsLoading(true);
    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      setStrategies(prev => prev.map(strategy => 
        strategy.id === strategyId 
          ? { ...strategy, isActive: !strategy.isActive, status: !strategy.isActive ? 'active' : 'paused' }
          : strategy
      ));
    } catch (error) {
      console.error('Failed to toggle strategy:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteStrategy = async (strategyId: number) => {
    if (window.confirm('Are you sure you want to delete this strategy?')) {
      try {
        // Simulate API call
        await new Promise(resolve => setTimeout(resolve, 500));
        setStrategies(prev => prev.filter(strategy => strategy.id !== strategyId));
      } catch (error) {
        console.error('Failed to delete strategy:', error);
      }
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'bg-success-100 text-success-800 dark:bg-success-900 dark:text-success-200';
      case 'paused':
        return 'bg-warning-100 text-warning-800 dark:bg-warning-900 dark:text-warning-200';
      case 'error':
        return 'bg-danger-100 text-danger-800 dark:bg-danger-900 dark:text-danger-200';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200';
    }
  };

  const getPnlColor = (pnl: string) => {
    return pnl.startsWith('+') ? 'text-success-600 dark:text-success-400' : 'text-danger-600 dark:text-danger-400';
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
            Strategy Management
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Monitor and manage your automated trading strategies
          </p>
        </div>
        <div className="mt-4 sm:mt-0">
          <button className="btn-primary inline-flex items-center">
            <Plus className="h-4 w-4 mr-2" />
            New Strategy
          </button>
        </div>
      </motion.div>

      {/* Strategy Overview Cards */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.1 }}
        className="grid grid-cols-1 md:grid-cols-4 gap-6"
      >
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="p-3 rounded-lg bg-primary-100 dark:bg-primary-900">
                <TrendingUp className="h-6 w-6 text-primary-600 dark:text-primary-400" />
              </div>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Total Strategies
              </p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {strategies.length}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="p-3 rounded-lg bg-success-100 dark:bg-success-900">
                <Play className="h-6 w-6 text-success-600 dark:text-success-400" />
              </div>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Active Strategies
              </p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {strategies.filter(s => s.isActive).length}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="p-3 rounded-lg bg-accent-100 dark:bg-accent-900">
                <BarChart3 className="h-6 w-6 text-accent-600 dark:text-accent-400" />
              </div>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Total P&L
              </p>
              <p className="text-2xl font-bold text-success-600 dark:text-success-400">
                +$3,159.00
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="p-3 rounded-lg bg-warning-100 dark:bg-warning-900">
                <Activity className="h-6 w-6 text-warning-600 dark:text-warning-400" />
              </div>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Total Trades
              </p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                135
              </p>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Strategies Table */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.2 }}
        className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden"
      >
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white">
            Trading Strategies
          </h3>
        </div>
        
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead className="bg-gray-50 dark:bg-gray-700">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Strategy
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  P&L
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Performance
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Last Trade
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
              {strategies.map((strategy) => (
                <tr key={strategy.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div>
                      <div className="text-sm font-medium text-gray-900 dark:text-white">
                        {strategy.name}
                      </div>
                      <div className="text-sm text-gray-500 dark:text-gray-400">
                        {strategy.type} • {strategy.pair}
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(strategy.status)}`}>
                      {strategy.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className={`text-sm font-medium ${getPnlColor(strategy.pnl)}`}>
                      {strategy.pnl}
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      {strategy.pnlPercent}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900 dark:text-white">
                      {strategy.trades} trades
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      {strategy.winRate} win rate
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                    <div className="flex items-center">
                      <Clock className="h-4 w-4 mr-1" />
                      {strategy.lastTrade}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => handleToggleStrategy(strategy.id)}
                        disabled={isLoading}
                        className={`p-2 rounded-lg transition-colors duration-200 ${
                          strategy.isActive
                            ? 'text-warning-600 hover:text-warning-700 hover:bg-warning-50 dark:hover:bg-warning-900/20'
                            : 'text-success-600 hover:text-success-700 hover:bg-success-50 dark:hover:bg-success-900/20'
                        }`}
                        title={strategy.isActive ? 'Pause Strategy' : 'Start Strategy'}
                      >
                        {strategy.isActive ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                      </button>
                      
                      <button
                        className="p-2 rounded-lg text-primary-600 hover:text-primary-700 hover:bg-primary-50 dark:hover:bg-primary-900/20 transition-colors duration-200"
                        title="View Details"
                      >
                        <Eye className="h-4 w-4" />
                      </button>
                      
                      <button
                        className="p-2 rounded-lg text-secondary-600 hover:text-secondary-700 hover:bg-secondary-50 dark:hover:bg-secondary-900/20 transition-colors duration-200"
                        title="Edit Strategy"
                      >
                        <Edit className="h-4 w-4" />
                      </button>
                      
                      <button
                        onClick={() => handleDeleteStrategy(strategy.id)}
                        className="p-2 rounded-lg text-danger-600 hover:text-danger-700 hover:bg-danger-50 dark:hover:bg-danger-900/20 transition-colors duration-200"
                        title="Delete Strategy"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </motion.div>

      {/* Empty State */}
      {strategies.length === 0 && (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5 }}
          className="text-center py-12"
        >
          <div className="mx-auto h-24 w-24 text-gray-400 dark:text-gray-600 mb-4">
            <TrendingUp className="h-24 w-24" />
          </div>
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
            No strategies yet
          </h3>
          <p className="text-gray-500 dark:text-gray-400 mb-6">
            Get started by creating your first automated trading strategy
          </p>
          <button className="btn-primary inline-flex items-center">
            <Plus className="h-4 w-4 mr-2" />
            Create Strategy
          </button>
        </motion.div>
      )}
    </div>
  );
};

export default StrategyManagement;
