import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
  TrendingUp, 
  TrendingDown, 
  DollarSign, 
  Activity, 
  Users, 
  Shield,
  ArrowUpRight,
  ArrowDownRight,
  Eye,
  Settings
} from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts';

// Mock data - replace with real API calls
const mockChartData = [
  { time: '00:00', price: 45000, volume: 1200 },
  { time: '04:00', price: 46500, volume: 1500 },
  { time: '08:00', price: 45800, volume: 1100 },
  { time: '12:00', price: 47200, volume: 1800 },
  { time: '16:00', price: 46800, volume: 1400 },
  { time: '20:00', price: 47500, volume: 1600 },
  { time: '24:00', price: 48200, volume: 1900 },
];

const mockTrades = [
  { id: 1, pair: 'BTC/USDT', type: 'buy', amount: 0.5, price: 47500, time: '2 min ago', status: 'completed' },
  { id: 2, pair: 'ETH/USDT', type: 'sell', amount: 2.0, price: 3200, time: '5 min ago', status: 'completed' },
  { id: 3, pair: 'BTC/USDT', type: 'buy', amount: 0.3, price: 47400, time: '8 min ago', status: 'pending' },
  { id: 4, pair: 'ADA/USDT', type: 'sell', amount: 1000, price: 0.45, time: '12 min ago', status: 'completed' },
];

const Dashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState('overview');
  const [isLoading, setIsLoading] = useState(false);

  const stats = [
    {
      name: 'Total Portfolio Value',
      value: '$125,430.50',
      change: '+12.5%',
      changeType: 'positive',
      icon: DollarSign,
    },
    {
      name: '24h P&L',
      value: '+$8,245.30',
      change: '+6.8%',
      changeType: 'positive',
      icon: TrendingUp,
    },
    {
      name: 'Active Strategies',
      value: '3',
      change: '+1',
      changeType: 'positive',
      icon: Activity,
    },
    {
      name: 'Total Trades',
      value: '1,247',
      change: '+23',
      changeType: 'positive',
      icon: Users,
    },
  ];

  const quickActions = [
    { name: 'View Portfolio', icon: Eye, href: '/portfolio', color: 'primary' },
    { name: 'New Strategy', icon: TrendingUp, href: '/strategy', color: 'success' },
    { name: 'Trade History', icon: Activity, href: '/history', color: 'warning' },
    { name: 'Settings', icon: Settings, href: '/settings', color: 'secondary' },
  ];

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
            Dashboard
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Welcome back! Here's what's happening with your portfolio today.
          </p>
        </div>
        <div className="mt-4 sm:mt-0">
          <span className="text-sm text-gray-500 dark:text-gray-400">
            Last updated: {new Date().toLocaleTimeString()}
          </span>
        </div>
      </motion.div>

      {/* Stats Grid */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.1 }}
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6"
      >
        {stats.map((stat, index) => (
          <motion.div
            key={stat.name}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 + index * 0.1 }}
            className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6"
          >
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className={`p-3 rounded-lg ${
                  stat.changeType === 'positive' 
                    ? 'bg-success-100 dark:bg-success-900' 
                    : 'bg-danger-100 dark:bg-danger-900'
                }`}>
                  <stat.icon className={`h-6 w-6 ${
                    stat.changeType === 'positive' 
                      ? 'text-success-600 dark:text-success-400' 
                      : 'text-danger-600 dark:text-danger-400'
                  }`} />
                </div>
              </div>
              <div className="ml-4 flex-1">
                <p className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
                  {stat.name}
                </p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {stat.value}
                </p>
              </div>
            </div>
            <div className="mt-4 flex items-center">
              {stat.changeType === 'positive' ? (
                <ArrowUpRight className="h-4 w-4 text-success-500" />
              ) : (
                <ArrowDownRight className="h-4 w-4 text-danger-500" />
              )}
              <span className={`ml-1 text-sm font-medium ${
                stat.changeType === 'positive' ? 'text-success-600 dark:text-success-400' : 'text-danger-600 dark:text-danger-400'
              }`}>
                {stat.change}
              </span>
              <span className="ml-2 text-sm text-gray-500 dark:text-gray-400">
                from last month
              </span>
            </div>
          </motion.div>
        ))}
      </motion.div>

      {/* Charts and Content Tabs */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.2 }}
        className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700"
      >
        {/* Tab Navigation */}
        <div className="border-b border-gray-200 dark:border-gray-700">
          <nav className="flex space-x-8 px-6" aria-label="Tabs">
            {['overview', 'trading', 'analytics'].map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`py-4 px-1 border-b-2 font-medium text-sm capitalize ${
                  activeTab === tab
                    ? 'border-primary-500 text-primary-600 dark:text-primary-400'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
                }`}
              >
                {tab}
              </button>
            ))}
          </nav>
        </div>

        {/* Tab Content */}
        <div className="p-6">
          {activeTab === 'overview' && (
            <div className="space-y-6">
              {/* Price Chart */}
              <div>
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                  Portfolio Performance (24h)
                </h3>
                <div className="h-80">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={mockChartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                      <XAxis dataKey="time" stroke="#9CA3AF" />
                      <YAxis stroke="#9CA3AF" />
                      <Tooltip 
                        contentStyle={{ 
                          backgroundColor: '#1F2937', 
                          border: 'none', 
                          borderRadius: '8px',
                          color: '#F9FAFB'
                        }}
                      />
                      <Area 
                        type="monotone" 
                        dataKey="price" 
                        stroke="#3B82F6" 
                        fill="#3B82F6" 
                        fillOpacity={0.1}
                        strokeWidth={2}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Quick Actions */}
              <div>
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                  Quick Actions
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {quickActions.map((action) => (
                    <button
                      key={action.name}
                      className="flex flex-col items-center p-4 bg-gray-50 dark:bg-gray-700 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors duration-200"
                    >
                      <div className={`p-3 rounded-lg mb-3 ${
                        action.color === 'primary' ? 'bg-primary-100 dark:bg-primary-900' :
                        action.color === 'success' ? 'bg-success-100 dark:bg-success-900' :
                        action.color === 'warning' ? 'bg-warning-100 dark:bg-warning-900' :
                        'bg-secondary-100 dark:bg-secondary-900'
                      }`}>
                        <action.icon className={`h-6 w-6 ${
                          action.color === 'primary' ? 'text-primary-600 dark:text-primary-400' :
                          action.color === 'success' ? 'text-success-600 dark:text-success-400' :
                          action.color === 'warning' ? 'text-warning-600 dark:text-warning-400' :
                          'text-secondary-600 dark:text-secondary-400'
                        }`} />
                      </div>
                      <span className="text-sm font-medium text-gray-900 dark:text-white text-center">
                        {action.name}
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'trading' && (
            <div>
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                Recent Trades
              </h3>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                  <thead className="bg-gray-50 dark:bg-gray-700">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Pair
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Type
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Amount
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Price
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Time
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Status
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                    {mockTrades.map((trade) => (
                      <tr key={trade.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">
                          {trade.pair}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                            trade.type === 'buy' 
                              ? 'bg-success-100 text-success-800 dark:bg-success-900 dark:text-success-200'
                              : 'bg-danger-100 text-danger-800 dark:bg-danger-900 dark:text-danger-200'
                          }`}>
                            {trade.type.toUpperCase()}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                          {trade.amount}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                          ${trade.price.toLocaleString()}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                          {trade.time}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                            trade.status === 'completed' 
                              ? 'bg-success-100 text-success-800 dark:bg-success-900 dark:text-success-200'
                              : 'bg-warning-100 text-warning-800 dark:bg-warning-900 dark:text-warning-200'
                          }`}>
                            {trade.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {activeTab === 'analytics' && (
            <div>
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                Trading Analytics
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-6">
                  <h4 className="text-md font-medium text-gray-900 dark:text-white mb-4">
                    Win Rate
                  </h4>
                  <div className="text-3xl font-bold text-success-600 dark:text-success-400">
                    68.5%
                  </div>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
                    Based on last 100 trades
                  </p>
                </div>
                <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-6">
                  <h4 className="text-md font-medium text-gray-900 dark:text-white mb-4">
                    Average Trade Duration
                  </h4>
                  <div className="text-3xl font-bold text-primary-600 dark:text-primary-400">
                    2.4h
                  </div>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
                    Median hold time
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
};

export default Dashboard;
