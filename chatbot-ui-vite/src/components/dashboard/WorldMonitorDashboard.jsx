import React, { useState, useEffect } from 'react';
import { AlertCircle, Globe, TrendingUp, Shield, Zap, Activity, Wind, Waves } from 'lucide-react';
import axios from 'axios';

const WorldMonitorDashboard = () => {
  const [globalSituation, setGlobalSituation] = useState(null);
  const [militaryActivity, setMilitaryActivity] = useState(null);
  const [infrastructure, setInfrastructure] = useState(null);
  const [financialMarkets, setFinancialMarkets] = useState(null);
  const [energyStatus, setEnergyStatus] = useState(null);
  const [cyberThreats, setCyberThreats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('global');
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, 60000);
    return () => clearInterval(interval);
  }, []);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const baseURL = 'http://localhost:5001/api/intelligence';

      const [
        globalRes,
        militaryRes,
        infraRes,
        financialRes,
        energyRes,
        cyberRes
      ] = await Promise.all([
        axios.get(`${baseURL}/global-situation`),
        axios.get(`${baseURL}/military-activity`),
        axios.get(`${baseURL}/infrastructure`),
        axios.get(`${baseURL}/financial-markets`),
        axios.get(`${baseURL}/energy`),
        axios.get(`${baseURL}/cyber-threats`)
      ]);

      setGlobalSituation(globalRes.data);
      setMilitaryActivity(militaryRes.data);
      setInfrastructure(infraRes.data);
      setFinancialMarkets(financialRes.data);
      setEnergyStatus(energyRes.data);
      setCyberThreats(cyberRes.data);
      setError(null);
    } catch (err) {
      setError('Failed to fetch world monitor data');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const getThreatColor = (level) => {
    const colors = {
      LOW: 'text-green-500 bg-green-50',
      MEDIUM: 'text-yellow-500 bg-yellow-50',
      HIGH: 'text-orange-500 bg-orange-50',
      CRITICAL: 'text-red-500 bg-red-50'
    };
    return colors[level] || colors.MEDIUM;
  };

  const RiskBadge = ({ level }) => (
    <span className={`px-3 py-1 rounded-full text-sm font-semibold ${getThreatColor(level)}`}>
      {level}
    </span>
  );

  const GlobalSituation = () => (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div className="bg-gradient-to-br from-red-50 to-red-100 p-6 rounded-lg border border-red-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-red-600">Threat Level</p>
              <p className="text-3xl font-bold text-red-700 mt-2">
                {globalSituation?.threat_level}
              </p>
            </div>
            <AlertCircle className="w-12 h-12 text-red-500" />
          </div>
        </div>

        <div className="bg-gradient-to-br from-orange-50 to-orange-100 p-6 rounded-lg border border-orange-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-orange-600">Escalation Index</p>
              <p className="text-3xl font-bold text-orange-700 mt-2">
                {globalSituation?.escalation_index?.toFixed(1)}
              </p>
            </div>
            <TrendingUp className="w-12 h-12 text-orange-500" />
          </div>
        </div>

        <div className="bg-gradient-to-br from-blue-50 to-blue-100 p-6 rounded-lg border border-blue-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-blue-600">Stability Score</p>
              <p className="text-3xl font-bold text-blue-700 mt-2">
                {globalSituation?.stability_score?.toFixed(1)}/100
              </p>
            </div>
            <Globe className="w-12 h-12 text-blue-500" />
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Critical Alerts</h3>
        <div className="space-y-3">
          {globalSituation?.alerts?.map((alert, idx) => (
            <div key={idx} className="flex items-start gap-3 p-3 bg-red-50 rounded-lg border border-red-200">
              <AlertCircle className="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0" />
              <div className="flex-1">
                <p className="font-medium text-gray-900">{alert.category}</p>
                <p className="text-sm text-gray-600">{alert.description}</p>
                <p className="text-xs text-gray-500 mt-1">{alert.location}</p>
              </div>
              <RiskBadge level={alert.severity} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  const MilitaryTracking = () => (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Shield className="w-5 h-5" /> Aircraft Movements
          </h3>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-gray-600">Active Flights:</span>
              <span className="font-bold text-gray-900">{militaryActivity?.aircraft_movements?.active_flights}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Anomalies:</span>
              <span className="font-bold text-red-600">{militaryActivity?.aircraft_movements?.anomalies}</span>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Waves className="w-5 h-5" /> Naval Movements
          </h3>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-gray-600">Active Vessels:</span>
              <span className="font-bold text-gray-900">{militaryActivity?.naval_movements?.active_vessels}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Carrier Groups:</span>
              <span className="font-bold text-gray-900">{militaryActivity?.naval_movements?.carrier_groups}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  const InfrastructureStatus = () => (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <Zap className="w-6 h-6 text-yellow-500 mb-2" />
          <p className="text-sm font-medium text-gray-600">Power Grids</p>
          <p className="text-lg font-bold mt-1 text-gray-900">NORMAL</p>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <Activity className="w-6 h-6 text-blue-500 mb-2" />
          <p className="text-sm font-medium text-gray-600">Communication</p>
          <p className="text-lg font-bold mt-1 text-gray-900">4/480</p>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <Wind className="w-6 h-6 text-orange-500 mb-2" />
          <p className="text-sm font-medium text-gray-600">Pipelines</p>
          <p className="text-lg font-bold mt-1 text-gray-900">{infrastructure?.pipelines?.disruptions || 5}</p>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <Globe className="w-6 h-6 text-purple-500 mb-2" />
          <p className="text-sm font-medium text-gray-600">Ports</p>
          <p className="text-lg font-bold mt-1 text-gray-900">{infrastructure?.ports?.affected_ports || 23}</p>
        </div>
      </div>
    </div>
  );

  const FinancialMetrics = () => (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <p className="text-sm font-medium text-gray-600 mb-2">S&P 500</p>
          <p className="text-2xl font-bold text-gray-900">{financialMarkets?.stock_markets?.us_markets?.change || '+0.5%'}</p>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <p className="text-sm font-medium text-gray-600 mb-2">Gold Price</p>
          <p className="text-2xl font-bold text-gray-900">${financialMarkets?.commodities?.gold || '2,150'}</p>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <p className="text-sm font-medium text-gray-600 mb-2">WTI Crude</p>
          <p className="text-2xl font-bold text-gray-900">${financialMarkets?.energy_prices?.wti_crude || '85.50'}</p>
        </div>
      </div>
    </div>
  );

  const CyberThreatTracker = () => (
    <div className="space-y-6">
      <div className="bg-gradient-to-br from-red-50 to-red-100 p-6 rounded-lg border border-red-200">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-red-600">Cyber Threat Level</p>
            <p className="text-3xl font-bold text-red-700 mt-2">{cyberThreats?.threat_level || 'HIGH'}</p>
          </div>
          <Shield className="w-12 h-12 text-red-500" />
        </div>
      </div>
    </div>
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <Globe className="w-12 h-12 text-blue-500 mx-auto mb-4 animate-spin" />
          <p className="text-gray-600">Loading global intelligence data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">World Monitor Intelligence Dashboard</h1>
        <p className="text-gray-600 mb-6">Real-time global intelligence and monitoring</p>

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-800">{error}</p>
          </div>
        )}

        <div className="mb-6 border-b border-gray-200 flex gap-4 overflow-x-auto">
          {[
            { id: 'global', label: 'Global', icon: Globe },
            { id: 'military', label: 'Military', icon: Shield },
            { id: 'infrastructure', label: 'Infrastructure', icon: Activity },
            { id: 'financial', label: 'Markets', icon: TrendingUp },
            { id: 'cyber', label: 'Cyber', icon: AlertCircle }
          ].map(tab => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-4 py-3 font-medium border-b-2 transition-colors flex items-center gap-2 whitespace-nowrap ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-600 hover:text-gray-900'
                }`}
              >
                <Icon className="w-4 h-4" />
                {tab.label}
              </button>
            );
          })}
        </div>

        <div className="bg-white rounded-lg p-6">
          {activeTab === 'global' && <GlobalSituation />}
          {activeTab === 'military' && <MilitaryTracking />}
          {activeTab === 'infrastructure' && <InfrastructureStatus />}
          {activeTab === 'financial' && <FinancialMetrics />}
          {activeTab === 'cyber' && <CyberThreatTracker />}
        </div>

        <button
          onClick={fetchDashboardData}
          className="mt-6 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
        >
          Refresh Data
        </button>
      </div>
    </div>
  );
};

export default WorldMonitorDashboard;
