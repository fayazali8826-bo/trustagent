import { useState, useEffect } from 'react';
import { Shield, Plus, Activity, Key, AlertTriangle, CheckCircle, XCircle, RefreshCw } from 'lucide-react';
import { listAgents, registerOrg, registerAgent, logBehavior, getAuditTrail } from './api';

interface Agent {
  id: string;
  name: string;
  trust_score: number;
  status: string;
  capabilities: string[];
  last_seen: string;
}

interface BehaviorLog {
  action: string;
  is_anomaly: boolean;
  anomaly_score: number;
  timestamp: string;
}

function TrustBadge({ score, status }: { score: number; status: string }) {
  const color =
    status === 'active' ? 'bg-green-100 text-green-800' :
    status === 'warning' ? 'bg-yellow-100 text-yellow-800' :
    status === 'breach' ? 'bg-red-100 text-red-800' :
    'bg-gray-100 text-gray-800';

  const icon =
    status === 'active' ? <CheckCircle className="w-4 h-4" /> :
    status === 'warning' ? <AlertTriangle className="w-4 h-4" /> :
    <XCircle className="w-4 h-4" />;

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${color}`}>
      {icon} {score.toFixed(1)} — {status}
    </span>
  );
}

function TrustBar({ score }: { score: number }) {
  const color = score >= 80 ? 'bg-green-500' : score >= 50 ? 'bg-yellow-500' : 'bg-red-500';
  return (
    <div className="w-full bg-gray-200 rounded-full h-2">
      <div className={`${color} h-2 rounded-full transition-all duration-500`} style={{ width: `${score}%` }} />
    </div>
  );
}

export default function App() {
  const [apiKey, setApiKey] = useState(localStorage.getItem('api_key') || '');
  const [orgName, setOrgName] = useState('');
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [auditLogs, setAuditLogs] = useState<BehaviorLog[]>([]);
  const [newAgentName, setNewAgentName] = useState('');
  const [newAgentCaps, setNewAgentCaps] = useState('');
  const [behaviorAction, setBehaviorAction] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [activeTab, setActiveTab] = useState('dashboard');
  const [privateKey, setPrivateKey] = useState('');

  useEffect(() => {
    if (apiKey) fetchAgents();
  }, [apiKey]);

  const fetchAgents = async () => {
    try {
      const res = await listAgents();
      setAgents(res.data);
    } catch (e) {
      setMessage('Failed to fetch agents — check your API key');
    }
  };

  const handleRegisterOrg = async () => {
    if (!orgName) return;
    setLoading(true);
    try {
      const res = await registerOrg(orgName);
      const key = res.data.api_key;
      localStorage.setItem('api_key', key);
      setApiKey(key);
      setMessage(`✅ Organization created! API Key: ${key}`);
    } catch (e: any) {
      setMessage(`❌ ${e.response?.data?.detail || 'Error registering org'}`);
    }
    setLoading(false);
  };

  const handleRegisterAgent = async () => {
    if (!newAgentName) return;
    setLoading(true);
    try {
      const caps = newAgentCaps.split(',').map(c => c.trim()).filter(Boolean);
      const res = await registerAgent(newAgentName, caps);
      setPrivateKey(res.data.private_key);
      setMessage(`✅ Agent "${newAgentName}" created! Save the private key shown below.`);
      setNewAgentName('');
      setNewAgentCaps('');
      fetchAgents();
    } catch (e: any) {
      setMessage(`❌ ${e.response?.data?.detail || 'Error registering agent'}`);
    }
    setLoading(false);
  };

  const handleLogBehavior = async () => {
    if (!selectedAgent || !behaviorAction) return;
    setLoading(true);
    try {
      const res = await logBehavior(selectedAgent.id, behaviorAction, { timestamp: Date.now() });
      setMessage(`✅ Behavior logged — Trust Score: ${res.data.new_trust_score} | Anomaly: ${res.data.is_anomaly ? '🚨 YES' : '✅ NO'}`);
      setBehaviorAction('');
      fetchAgents();
    } catch (e: any) {
      setMessage(`❌ ${e.response?.data?.detail || 'Error logging behavior'}`);
    }
    setLoading(false);
  };

  const handleViewAudit = async (agent: Agent) => {
    setSelectedAgent(agent);
    setActiveTab('audit');
    try {
      const res = await getAuditTrail(agent.id);
      setAuditLogs(res.data.behavior_logs);
    } catch (e) {
      setMessage('Failed to load audit trail');
    }
  };

  if (!apiKey) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-2xl p-8 w-full max-w-md">
          <div className="flex items-center gap-3 mb-6">
            <Shield className="w-10 h-10 text-blue-600" />
            <div>
              <h1 className="text-2xl font-bold text-gray-900">TrustAgent</h1>
              <p className="text-sm text-gray-500">Agent-to-Agent Trust Infrastructure</p>
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Organization Name</label>
              <input
                className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="e.g. Acme Corp"
                value={orgName}
                onChange={e => setOrgName(e.target.value)}
              />
            </div>
            <button
              onClick={handleRegisterOrg}
              disabled={loading}
              className="w-full bg-blue-600 text-white py-2 rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? 'Creating...' : 'Create Organization'}
            </button>

            <div className="relative">
              <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-gray-300" /></div>
              <div className="relative flex justify-center text-sm"><span className="px-2 bg-white text-gray-500">or</span></div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Enter Existing API Key</label>
              <input
                className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="ta_..."
                value={orgName}
                onChange={e => {
                  localStorage.setItem('api_key', e.target.value);
                  setApiKey(e.target.value);
                }}
              />
            </div>
          </div>

          {message && <p className="mt-4 text-sm text-blue-600 bg-blue-50 p-3 rounded-lg">{message}</p>}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-slate-900 text-white px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Shield className="w-8 h-8 text-blue-400" />
          <div>
            <h1 className="text-xl font-bold">TrustAgent</h1>
            <p className="text-xs text-slate-400">Agent Trust Infrastructure</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-slate-400 hidden md:block">
            <Key className="w-3 h-3 inline mr-1" />{apiKey.slice(0, 20)}...
          </span>
          <button
            onClick={() => { localStorage.removeItem('api_key'); setApiKey(''); }}
            className="text-xs text-red-400 hover:text-red-300"
          >
            Logout
          </button>
        </div>
      </header>

      {/* Tabs */}
      <div className="bg-white border-b px-6">
        <nav className="flex gap-6">
          {['dashboard', 'register', 'behavior', 'audit'].map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`py-3 text-sm font-medium border-b-2 capitalize ${activeTab === tab ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}
            >
              {tab}
            </button>
          ))}
        </nav>
      </div>

      <main className="max-w-6xl mx-auto p-6">
        {message && (
          <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg text-sm text-blue-800">
            {message}
            <button onClick={() => setMessage('')} className="float-right text-blue-400 hover:text-blue-600">✕</button>
          </div>
        )}

        {/* Dashboard Tab */}
        {activeTab === 'dashboard' && (
          <div>
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold text-gray-900">Agent Network</h2>
              <button onClick={fetchAgents} className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700">
                <RefreshCw className="w-4 h-4" /> Refresh
              </button>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              {[
                { label: 'Total Agents', value: agents.length, color: 'blue' },
                { label: 'Active', value: agents.filter(a => a.status === 'active').length, color: 'green' },
                { label: 'Warning', value: agents.filter(a => a.status === 'warning').length, color: 'yellow' },
                { label: 'Breach', value: agents.filter(a => a.status === 'breach' || a.status === 'suspended').length, color: 'red' },
              ].map(stat => (
                <div key={stat.label} className="bg-white rounded-xl border p-4">
                  <p className="text-sm text-gray-500">{stat.label}</p>
                  <p className={`text-3xl font-bold text-${stat.color}-600`}>{stat.value}</p>
                </div>
              ))}
            </div>

            {/* Agent List */}
            {agents.length === 0 ? (
              <div className="bg-white rounded-xl border p-12 text-center">
                <Shield className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                <p className="text-gray-500">No agents yet. Go to Register tab to create your first agent.</p>
              </div>
            ) : (
              <div className="grid gap-4">
                {agents.map(agent => (
                  <div key={agent.id} className="bg-white rounded-xl border p-5 hover:shadow-md transition-shadow">
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <h3 className="font-semibold text-gray-900">{agent.name}</h3>
                        <p className="text-xs text-gray-400 mt-0.5">{agent.id}</p>
                      </div>
                      <TrustBadge score={agent.trust_score} status={agent.status} />
                    </div>
                    <TrustBar score={agent.trust_score} />
                    <div className="flex items-center justify-between mt-3">
                      <div className="flex gap-2 flex-wrap">
                        {agent.capabilities?.map(cap => (
                          <span key={cap} className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">{cap}</span>
                        ))}
                      </div>
                      <div className="flex gap-2">
                        <button
                          onClick={() => { setSelectedAgent(agent); setActiveTab('behavior'); }}
                          className="text-xs text-blue-600 hover:underline"
                        >
                          Log Behavior
                        </button>
                        <button
                          onClick={() => handleViewAudit(agent)}
                          className="text-xs text-purple-600 hover:underline"
                        >
                          Audit Trail
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Register Tab */}
        {activeTab === 'register' && (
          <div className="max-w-lg">
            <h2 className="text-xl font-bold text-gray-900 mb-6">Register New Agent</h2>
            <div className="bg-white rounded-xl border p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Agent Name</label>
                <input
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="e.g. PaymentAgent, EmailBot"
                  value={newAgentName}
                  onChange={e => setNewAgentName(e.target.value)}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Capabilities (comma separated)</label>
                <input
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="e.g. read_emails, send_slack, process_payments"
                  value={newAgentCaps}
                  onChange={e => setNewAgentCaps(e.target.value)}
                />
              </div>
              <button
                onClick={handleRegisterAgent}
                disabled={loading}
                className="w-full bg-blue-600 text-white py-2 rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 flex items-center justify-center gap-2"
              >
                <Plus className="w-4 h-4" />
                {loading ? 'Registering...' : 'Register Agent'}
              </button>
            </div>

            {privateKey && (
              <div className="mt-4 bg-yellow-50 border border-yellow-200 rounded-xl p-4">
                <p className="text-sm font-medium text-yellow-800 mb-2">⚠️ Save this private key — shown only once!</p>
                <pre className="text-xs text-yellow-700 bg-yellow-100 p-3 rounded overflow-auto max-h-40">{privateKey}</pre>
              </div>
            )}
          </div>
        )}

        {/* Behavior Tab */}
        {activeTab === 'behavior' && (
          <div className="max-w-lg">
            <h2 className="text-xl font-bold text-gray-900 mb-6">Log Agent Behavior</h2>
            <div className="bg-white rounded-xl border p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Select Agent</label>
                <select
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  value={selectedAgent?.id || ''}
                  onChange={e => setSelectedAgent(agents.find(a => a.id === e.target.value) || null)}
                >
                  <option value="">Choose an agent...</option>
                  {agents.map(a => (
                    <option key={a.id} value={a.id}>{a.name} — Trust: {a.trust_score}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Action</label>
                <input
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="e.g. send_email, read_database, process_payment"
                  value={behaviorAction}
                  onChange={e => setBehaviorAction(e.target.value)}
                />
              </div>
              <button
                onClick={handleLogBehavior}
                disabled={loading || !selectedAgent}
                className="w-full bg-purple-600 text-white py-2 rounded-lg font-medium hover:bg-purple-700 disabled:opacity-50 flex items-center justify-center gap-2"
              >
                <Activity className="w-4 h-4" />
                {loading ? 'Logging...' : 'Log Behavior & Score'}
              </button>
            </div>
          </div>
        )}

        {/* Audit Tab */}
        {activeTab === 'audit' && (
          <div>
            <h2 className="text-xl font-bold text-gray-900 mb-6">
              Audit Trail {selectedAgent && <span className="text-blue-600">— {selectedAgent.name}</span>}
            </h2>
            {!selectedAgent ? (
              <div className="bg-white rounded-xl border p-12 text-center">
                <p className="text-gray-500">Select an agent from the Dashboard to view its audit trail.</p>
              </div>
            ) : auditLogs.length === 0 ? (
              <div className="bg-white rounded-xl border p-12 text-center">
                <p className="text-gray-500">No behavior logs yet for this agent.</p>
              </div>
            ) : (
              <div className="bg-white rounded-xl border overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 border-b">
                    <tr>
                      <th className="text-left px-4 py-3 font-medium text-gray-600">Action</th>
                      <th className="text-left px-4 py-3 font-medium text-gray-600">Anomaly</th>
                      <th className="text-left px-4 py-3 font-medium text-gray-600">Score</th>
                      <th className="text-left px-4 py-3 font-medium text-gray-600">Timestamp</th>
                    </tr>
                  </thead>
                  <tbody>
                    {auditLogs.map((log, i) => (
                      <tr key={i} className={`border-b ${log.is_anomaly ? 'bg-red-50' : ''}`}>
                        <td className="px-4 py-3 font-mono">{log.action}</td>
                        <td className="px-4 py-3">
                          {log.is_anomaly
                            ? <span className="text-red-600 font-medium">🚨 YES</span>
                            : <span className="text-green-600">✅ No</span>}
                        </td>
                        <td className="px-4 py-3">{log.anomaly_score.toFixed(3)}</td>
                        <td className="px-4 py-3 text-gray-400">{new Date(log.timestamp).toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}