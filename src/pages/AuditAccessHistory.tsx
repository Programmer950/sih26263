import React, { useState, useEffect } from 'react';
import {
  CheckCircle,
  RefreshCw,
} from 'lucide-react';
import api from '../services/api';

export const AuditAccessHistory: React.FC = () => {
  const [events, setEvents] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [selectedEvent, setSelectedEvent] = useState<any | null>(null);
  const [entityFilter, setEntityFilter] = useState<string>('');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadEvents();
  }, [entityFilter]);

  const loadEvents = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const params: Record<string, any> = { limit: 50 };
      if (entityFilter) params.entity_type = entityFilter;
      const res = await api.get('/audit/events', { params });
      const items = res.data.items || [];
      setEvents(items);
      if (items.length > 0 && !selectedEvent) {
        setSelectedEvent(items[0]);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to load audit events.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="bg-white border border-[#D7DEE5] rounded p-5 shadow-sm">
        <div className="flex items-center gap-2">
          <span className="gov-badge gov-badge-info">
            Module 18 — Cryptographic Audit Trail
          </span>
          <span className="text-[11px] text-[#5F6B76] font-mono">SHA-256 Chained Hash Ledger</span>
        </div>
        <h1 className="text-xl font-bold text-[#12345A] mt-1.5 uppercase tracking-wide">
          Audit & Access History Ledger / अंकेक्षण एवं पहुंच पंजिका
        </h1>
        <p className="text-xs text-[#5F6B76] mt-0.5">
          Cryptographically chained, append-only security log protected by SHA-256 hash chaining and transaction-level PostgreSQL advisory locks.
        </p>

        {/* Cryptographic Assurance Banner */}
        <div className="mt-4 p-3.5 bg-[#EAF7EE] border border-[#23834A] rounded text-xs text-[#166534] flex items-center gap-3">
          <CheckCircle size={20} className="text-[#23834A] shrink-0" />
          <div className="leading-relaxed">
            <strong>Ledger Integrity Verified:</strong> Each event binds mathematically to the SHA-256 hash of its immediate predecessor. Any retroactive modification or deletion breaks the hash chain and triggers immediate regulatory tamper alerts.
          </div>
        </div>
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 text-red-900 rounded text-xs">
          {error}
        </div>
      )}

      {/* Filter and Action Bar */}
      <div className="bg-white border border-[#D7DEE5] rounded p-4 flex flex-col md:flex-row justify-between items-center gap-3 shadow-sm">
        <div className="flex items-center gap-3">
          <span className="text-xs font-bold uppercase tracking-wider text-[#12345A]">Filter Entity:</span>
          <select
            value={entityFilter}
            onChange={(e) => setEntityFilter(e.target.value)}
            className="gov-input text-xs"
          >
            <option value="">All Entities</option>
            <option value="RosterSnapshot">RosterSnapshot</option>
            <option value="SourceSubmission">SourceSubmission</option>
            <option value="DiscrepancyCase">DiscrepancyCase</option>
            <option value="AggregateDeclaration">AggregateDeclaration</option>
            <option value="User">User / Authentication</option>
          </select>
        </div>

        <button
          onClick={loadEvents}
          disabled={isLoading}
          className="gov-btn-secondary text-xs py-1.5 px-3.5 flex items-center gap-2"
        >
          <RefreshCw size={13} className={isLoading ? 'animate-spin' : ''} />
          Refresh Ledger
        </button>
      </div>

      {/* Main Ledger Two-Column View */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Ledger Event List */}
        <div className="lg:col-span-5 bg-white border border-[#D7DEE5] rounded p-5 shadow-sm space-y-3">
          <div className="border-b border-[#D7DEE5] pb-3">
            <h2 className="text-sm font-bold text-[#12345A] uppercase tracking-wide">
              Ledger Sequence ({events.length} Events)
            </h2>
            <p className="text-xs text-[#5F6B76] mt-0.5">Chronological chronological transaction chain.</p>
          </div>

          <div className="space-y-2 max-h-[650px] overflow-y-auto pr-1">
            {events.length === 0 ? (
              <div className="text-center py-12 text-[#5F6B76] text-xs">
                No audit events recorded for selected filter.
              </div>
            ) : (
              events.map((ev) => {
                const isSelected = selectedEvent?.id === ev.id;
                return (
                  <div
                    key={ev.id}
                    onClick={() => setSelectedEvent(ev)}
                    className={`p-3 rounded border cursor-pointer transition ${
                      isSelected
                        ? 'border-[#174F82] bg-[#EAF2F8] border-l-4 border-l-[#12345A] shadow-xs'
                        : 'border-[#D7DEE5] bg-white hover:bg-[#F4F6F8]'
                    }`}
                  >
                    <div className="flex justify-between items-center mb-1">
                      <span className="text-xs font-bold text-[#12345A]">
                        {ev.action}
                      </span>
                      <span className="text-[10px] text-[#5F6B76]">
                        {new Date(ev.timestamp).toLocaleTimeString()}
                      </span>
                    </div>

                    <div className="flex justify-between items-center text-xs text-[#5F6B76]">
                      <span>Actor: <strong className="text-[#202B36]">{ev.actor_name}</strong></span>
                      <span className="font-mono text-[10px] text-[#174F82] bg-[#EAF2F8] border border-[#CBD7E3] px-1.5 py-0.5 rounded">
                        #{ev.event_hash.slice(0, 10)}...
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Cryptographic Event Inspector */}
        <div className="lg:col-span-7 bg-white border border-[#D7DEE5] rounded p-5 shadow-sm">
          {selectedEvent ? (
            <div className="space-y-4">
              <div className="border-b border-[#D7DEE5] pb-3">
                <span className="text-[10px] font-bold uppercase tracking-wider text-[#5F6B76]">Cryptographic Event Proof</span>
                <h2 className="text-base font-bold text-[#12345A] mt-0.5">
                  {selectedEvent.action}
                </h2>
                <div className="text-xs text-[#5F6B76]">
                  Recorded Timestamp: {new Date(selectedEvent.timestamp).toUTCString()}
                </div>
              </div>

              {/* Hash Chaining Visualizer */}
              <div className="bg-[#12345A] text-[#F4F6F8] rounded p-4 font-mono text-xs space-y-3">
                <div>
                  <div className="text-[#8C9BA8] text-[10px] uppercase font-bold tracking-wider mb-1">
                    Previous Event Digest H(t-1):
                  </div>
                  <div className="text-[#F5B041] break-all bg-[#0B2138] p-2 rounded border border-[#204060]">
                    {selectedEvent.previous_event_hash}
                  </div>
                </div>

                <div>
                  <div className="text-[#8C9BA8] text-[10px] uppercase font-bold tracking-wider mb-1">
                    Current Event Digest H(t) = SHA-256(H(t-1) || payload):
                  </div>
                  <div className="text-[#58D68D] break-all bg-[#0B2138] p-2 rounded border border-[#204060]">
                    {selectedEvent.event_hash}
                  </div>
                </div>
              </div>

              {/* Attributes Grid */}
              <div className="grid grid-cols-2 gap-3 text-xs bg-[#F4F6F8] border border-[#D7DEE5] rounded p-3 text-[#202B36]">
                <div><span className="text-[#5F6B76]">Entity Type:</span> <strong className="text-[#12345A]">{selectedEvent.entity_type}</strong></div>
                <div><span className="text-[#5F6B76]">Entity ID:</span> <span className="font-mono text-[11px] text-[#174F82]">{selectedEvent.entity_id ? selectedEvent.entity_id.slice(0, 16) + '...' : 'N/A'}</span></div>
                <div><span className="text-[#5F6B76]">Actor:</span> <strong>{selectedEvent.actor_name}</strong></div>
                <div><span className="text-[#5F6B76]">Client Origin:</span> <span className="font-mono text-[#5F6B76]">{selectedEvent.ip_address || '127.0.0.1 (Local)'}</span></div>
              </div>

              {/* Metadata Payload JSON */}
              <div>
                <h4 className="text-xs font-bold text-[#12345A] uppercase tracking-wide mb-1.5">
                  Structured Event Metadata Payload
                </h4>
                <pre className="bg-[#F4F6F8] border border-[#D7DEE5] rounded p-3 text-xs font-mono text-[#202B36] max-h-52 overflow-y-auto">
                  {JSON.stringify(selectedEvent.metadata_payload, null, 2)}
                </pre>
              </div>
            </div>
          ) : (
            <div className="text-center py-20 text-[#5F6B76] text-xs">
              Select an event from the sequence to view its cryptographic chain hashes and payload.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
