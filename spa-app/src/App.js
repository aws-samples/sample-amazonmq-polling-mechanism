import React, { useState, useEffect, useCallback } from 'react';
import AWS from 'aws-sdk';

AWS.config.update({
  region: 'ap-southeast-2',
  credentials: new AWS.CognitoIdentityCredentials({
    IdentityPoolId: 'ap-southeast-2:7f2fee03-9a25-4b74-aef9-81b0e6ce557f'
  })
});

const dynamodb = new AWS.DynamoDB.DocumentClient();

// Allowed API endpoints - whitelist approach
const ALLOWED_API_BASE = 'https://nmhxzbemjr.ap-southeast-2.awsapprunner.com';
const ALLOWED_WS_BASE = 'wss://d02mcs693h.execute-api.ap-southeast-2.amazonaws.com/prod';

const validateUrl = (url, allowedBase) => {
  try {
    const urlObj = new URL(url);
    const baseObj = new URL(allowedBase);
    return urlObj.origin === baseObj.origin && url.startsWith(allowedBase);
  } catch {
    return false;
  }
};

const sanitizeId = (id) => {
  if (!id || typeof id !== 'string') {
    return null;
  }
  // Allow only alphanumeric characters, hyphens, and underscores
  const validIdPattern = /^[a-zA-Z0-9_-]+$/;
  return validIdPattern.test(id) ? id : null;
};

const safeFetch = async (endpoint, options = {}) => {
  const url = `${ALLOWED_API_BASE}${endpoint}`;
  if (!validateUrl(url, ALLOWED_API_BASE)) {
    throw new Error('Invalid URL');
  }
  return fetch(url, options);
};

function App() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [wsConnection, setWsConnection] = useState(null);
  const [sortField, setSortField] = useState('timestamp');
  const [sortOrder, setSortOrder] = useState('desc');
  const [queueStatus, setQueueStatus] = useState(null);
  const [mqLogs, setMqLogs] = useState([]);
  const [showMqPanel, setShowMqPanel] = useState(false);

  const fetchItems = useCallback(async () => {
    try {
      const result = await dynamodb.scan({
        TableName: 'DatabaseStack-DatabaseSpaTable3FEC3A88-1VVAD0QTH0EJ4'
      }).promise();
      
      setItems(result.Items || []);
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (error) {
      console.error('Error fetching items:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchQueueStatus = useCallback(async () => {
    try {
      const response = await safeFetch('/api/queue/status');
      const data = await response.json();
      setQueueStatus(data);
      
      const newLogs = [];
      
      if (data.statistics) {
        const stats = data.statistics;
        const pending = Math.max(0, stats.totalEnqueued - stats.totalDequeued);
        newLogs.push({
          timestamp: new Date().toLocaleTimeString(),
          type: 'stats',
          message: '📊 Stats: ' + stats.totalEnqueued + ' queued, ' + stats.totalDequeued + ' processed, ' + pending + ' pending'
        });
      }
      
      if (data.recentActivity && data.recentActivity.length > 0) {
        const activityLogs = data.recentActivity.map(activity => {
          const [timestamp, message] = activity.split(': ');
          return {
            timestamp: new Date(timestamp).toLocaleTimeString(),
            type: message.includes('QUEUED') ? 'queued' : 'dequeued',
            message: message
          };
        });
        newLogs.push(...activityLogs);
      }
      
      setMqLogs(newLogs);
    } catch (error) {
      console.error('Error fetching queue status:', error);
      setQueueStatus({ status: 'error', error: error.message });
      
      const logEntry = {
        timestamp: new Date().toLocaleTimeString(),
        type: 'error',
        message: 'Queue error: ' + error.message
      };
      setMqLogs([logEntry]);
    }
  }, []);

  const connectWebSocket = useCallback(() => {
    if (!validateUrl(ALLOWED_WS_BASE, ALLOWED_WS_BASE)) {
      console.error('Invalid WebSocket URL');
      return;
    }
    console.log('Connecting to Simple WebSocket (DynamoDB Streams):', ALLOWED_WS_BASE);
    const ws = new WebSocket(ALLOWED_WS_BASE);
    
    ws.onopen = () => {
      console.log('WebSocket connected');
      setIsConnected(true);
    };
    
    ws.onmessage = (event) => {
      try {
        const changeData = JSON.parse(event.data);
        console.log('Received DynamoDB change:', changeData);
        
        const { eventName, data, oldData } = changeData;
        
        setItems(prevItems => {
          switch (eventName) {
            case 'INSERT':
              return [data, ...prevItems];
            case 'MODIFY':
              const modifyIndex = prevItems.findIndex(item => item.id === data.id);
              if (modifyIndex >= 0) {
                const newItems = [...prevItems];
                newItems[modifyIndex] = data;
                return newItems;
              }
              return prevItems;
            case 'REMOVE':
              return prevItems.filter(item => item.id !== data.id);
            default:
              return prevItems;
          }
        });
        
        setLastUpdated(new Date().toLocaleTimeString());
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };
    
    ws.onclose = () => {
      console.log('WebSocket disconnected');
      setIsConnected(false);
      setTimeout(connectWebSocket, 3000);
    };
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
    
    setWsConnection(ws);
  }, []);

  useEffect(() => {
    fetchItems();
    fetchQueueStatus();
    connectWebSocket();
    
    return () => {
      if (wsConnection) {
        wsConnection.close();
      }
    };
  }, [fetchItems, fetchQueueStatus, connectWebSocket]);

  useEffect(() => {
    const interval = setInterval(fetchQueueStatus, 5000);
    return () => clearInterval(interval);
  }, [fetchQueueStatus]);

  const toggleConnection = () => {
    if (wsConnection && isConnected) {
      wsConnection.close();
      setIsConnected(false);
    } else {
      connectWebSocket();
    }
  };

  const addSampleItem = async () => {
    try {
      const priorities = ['High', 'Medium', 'Low'];
      const statuses = ['Active', 'Pending', 'Completed'];
      const types = ['Task', 'Bug', 'Feature', 'Issue'];
      
      const newItem = {
        id: Date.now().toString(),
        title: types[Math.floor(Math.random() * types.length)] + ' #' + Math.floor(Math.random() * 1000),
        message: 'Sample item created at ' + new Date().toISOString(),
        priority: priorities[Math.floor(Math.random() * priorities.length)],
        status: statuses[Math.floor(Math.random() * statuses.length)],
        timestamp: Date.now(),
        createdAt: new Date().toISOString(),
        lastModified: new Date().toISOString()
      };

      await dynamodb.put({
        TableName: 'DatabaseStack-DatabaseSpaTable3FEC3A88-1VVAD0QTH0EJ4',
        Item: newItem
      }).promise();

      fetchItems();
    } catch (error) {
      console.error('Error adding item:', error);
    }
  };

  const sortItems = (items) => {
    return [...items].sort((a, b) => {
      let aVal = a[sortField] || '';
      let bVal = b[sortField] || '';
      
      if (sortField === 'timestamp') {
        aVal = Number(aVal) || 0;
        bVal = Number(bVal) || 0;
      }
      
      if (sortOrder === 'asc') {
        return aVal > bVal ? 1 : -1;
      }
      return aVal < bVal ? 1 : -1;
    });
  };

  const getPriorityColor = (priority) => {
    switch(priority) {
      case 'High': return '#dc3545';
      case 'Medium': return '#ffc107';
      case 'Low': return '#28a745';
      default: return '#6c757d';
    }
  };

  const getStatusColor = (status) => {
    switch(status) {
      case 'Active': return '#007bff';
      case 'Pending': return '#ffc107';
      case 'Completed': return '#28a745';
      default: return '#6c757d';
    }
  };

  if (loading) {
    return (
      <div style={{ padding: '20px', textAlign: 'center' }}>
        <h1>Loading...</h1>
      </div>
    );
  }

  return (
    <div style={{ padding: '20px', fontFamily: 'Arial, sans-serif' }}>
      <header style={{ marginBottom: '30px', textAlign: 'center', padding: '20px 0' }}>
        <h1 style={{ 
          fontSize: '2.5rem', 
          color: '#2c3e50', 
          marginBottom: '10px',
          fontWeight: '300'
        }}>Priority-Based Message Processing Demo</h1>
        <p style={{ 
          fontSize: '1.2rem', 
          color: '#7f8c8d', 
          marginBottom: '10px'
        }}>Real-time DynamoDB updates with JMS priority queuing</p>
        <p style={{
          fontSize: '1rem',
          color: '#e74c3c',
          fontWeight: '500',
          marginBottom: '20px'
        }}>🚀 High priority messages bypass delay timer and process immediately</p>
        <div style={{
          display: 'flex',
          justifyContent: 'center',
          gap: '30px',
          flexWrap: 'wrap',
          fontSize: '0.9rem',
          color: '#34495e'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ color: '#e74c3c', fontSize: '1.2rem' }}>🔴</span>
            <span>High Priority (9)</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ color: '#f39c12', fontSize: '1.2rem' }}>🟡</span>
            <span>Medium Priority (4)</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ color: '#27ae60', fontSize: '1.2rem' }}>🟢</span>
            <span>Low Priority (0)</span>
          </div>
        </div>
      </header>

      <div style={{ marginBottom: '20px', display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
        <button 
          onClick={toggleConnection}
          style={{
            padding: '10px 20px',
            backgroundColor: isConnected ? '#28a745' : '#dc3545',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer'
          }}
        >
          {isConnected ? '🟢 Connected' : '🔴 Disconnected'}
        </button>
        
        <button 
          onClick={() => setShowMqPanel(!showMqPanel)}
          style={{
            padding: '10px 20px',
            backgroundColor: showMqPanel ? '#dc3545' : '#17a2b8',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer'
          }}
        >
          {showMqPanel ? 'Hide MQ Panel' : 'Show MQ Panel'}
        </button>
        
        <button 
          onClick={async () => {
            if (window.confirm('Are you sure you want to delete ALL items from DynamoDB? This cannot be undone!')) {
              try {
                const response = await safeFetch('/api/items/delete-all', {
                  method: 'DELETE'
                });
                const result = await response.json();
                if (result.status === 'success') {
                  fetchItems();
                  alert('Successfully deleted ' + (result.deletedCount || 0) + ' items');
                } else {
                  alert('Failed to delete items: ' + result.message);
                }
              } catch (error) {
                console.error('Failed to delete all items:', error);
                alert('Error deleting items');
              }
            }
          }}
          style={{
            padding: '10px 20px',
            backgroundColor: '#dc3545',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer'
          }}
        >
          Delete All Items
        </button>
      </div>

      <div style={{ marginBottom: '20px', fontSize: '14px', color: '#666' }}>
        <span style={{ fontWeight: '500' }}>WebSocket: {isConnected ? '🟢 Real-time Connected' : '🔴 Disconnected'}</span>
        {lastUpdated && <span> | Last updated: {lastUpdated}</span>}
        <span> | Active messages: <strong>{items.length}</strong></span>
      </div>

      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h2 style={{ color: '#2c3e50', fontSize: '1.5rem' }}>Live Message Queue Processing</h2>
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            <span>Sort by:</span>
            <select 
              value={sortField} 
              onChange={(e) => setSortField(e.target.value)}
              style={{ padding: '5px', borderRadius: '4px', border: '1px solid #ccc' }}
            >
              <option value="timestamp">Timestamp</option>
              <option value="priority">Priority</option>
              <option value="status">Status</option>
              <option value="title">Title</option>
            </select>
            <button 
              onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
              style={{
                padding: '5px 10px',
                backgroundColor: '#f8f9fa',
                border: '1px solid #ccc',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              {sortOrder === 'asc' ? '↑' : '↓'}
            </button>
          </div>
        </div>
        
        {items.length === 0 ? (
          <div style={{ 
            padding: '40px', 
            textAlign: 'center', 
            backgroundColor: '#f8f9fa', 
            borderRadius: '8px',
            color: '#6c757d'
          }}>
            <h3 style={{ margin: '0 0 10px 0', color: '#34495e' }}>Ready for Demo</h3>
            <p>Use the test script to create priority-based messages:</p>
            <div style={{ fontFamily: 'monospace', fontSize: '14px', margin: '15px 0' }}>
              <div>./test-api.sh 8 "Low Priority" "8s delay" "Low"</div>
              <div>./test-api.sh 5 "High Priority" "5s delay" "High"</div>
            </div>
            <p style={{ fontSize: '14px', color: '#e74c3c', fontWeight: '500' }}>🚀 High priority messages bypass delay timer and process immediately</p>
            <p style={{ fontSize: '14px', color: '#7f8c8d' }}>Then processed in JMS priority order: High (9) → Medium (4) → Low (0)</p>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ 
              width: '100%', 
              borderCollapse: 'collapse',
              backgroundColor: '#fff',
              borderRadius: '8px',
              overflow: 'hidden',
              boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
            }}>
              <thead>
                <tr style={{ backgroundColor: '#f8f9fa' }}>
                  <th style={{ padding: '12px', textAlign: 'left', borderBottom: '2px solid #dee2e6', minWidth: '180px' }}>ID</th>
                  <th style={{ padding: '12px', textAlign: 'left', borderBottom: '2px solid #dee2e6' }}>Title</th>
                  <th style={{ padding: '12px', textAlign: 'left', borderBottom: '2px solid #dee2e6' }}>Priority</th>
                  <th style={{ padding: '12px', textAlign: 'left', borderBottom: '2px solid #dee2e6' }}>Status</th>
                  <th style={{ padding: '12px', textAlign: 'left', borderBottom: '2px solid #dee2e6' }}>Message</th>
                  <th style={{ padding: '12px', textAlign: 'left', borderBottom: '2px solid #dee2e6' }}>Delay</th>
                  <th style={{ padding: '12px', textAlign: 'left', borderBottom: '2px solid #dee2e6' }}>Created</th>
                  <th style={{ padding: '12px', textAlign: 'left', borderBottom: '2px solid #dee2e6' }}>Modified</th>
                  <th style={{ padding: '12px', textAlign: 'center', borderBottom: '2px solid #dee2e6' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {sortItems(items).map((item, index) => (
                  <tr key={item.id} style={{ 
                    backgroundColor: index % 2 === 0 ? '#fff' : '#f8f9fa',
                    borderBottom: '1px solid #dee2e6'
                  }}>
                    <td style={{ padding: '12px', fontFamily: 'monospace', fontSize: '11px', wordBreak: 'break-all', minWidth: '180px' }}>
                      {item.id}
                    </td>
                    <td style={{ padding: '12px', fontWeight: 'bold' }}>
                      {item.title || 'N/A'}
                    </td>
                    <td style={{ padding: '12px' }}>
                      <span style={{
                        padding: '4px 8px',
                        borderRadius: '12px',
                        fontSize: '12px',
                        fontWeight: 'bold',
                        color: 'white',
                        backgroundColor: getPriorityColor(item.priority)
                      }}>
                        {item.priority || 'N/A'}
                      </span>
                    </td>
                    <td style={{ padding: '12px' }}>
                      <span style={{
                        padding: '4px 8px',
                        borderRadius: '12px',
                        fontSize: '12px',
                        fontWeight: 'bold',
                        color: 'white',
                        backgroundColor: getStatusColor(item.status)
                      }}>
                        {item.status || 'N/A'}
                      </span>
                    </td>
                    <td style={{ padding: '12px', maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {item.message || 'No message'}
                    </td>
                    <td style={{ padding: '12px', textAlign: 'center' }}>
                      <span style={{
                        padding: '4px 8px',
                        borderRadius: '12px',
                        fontSize: '12px',
                        fontWeight: 'bold',
                        color: 'white',
                        backgroundColor: item.delay > 0 ? '#ffc107' : '#28a745'
                      }}>
                        {item.delay || 0}s
                      </span>
                    </td>
                    <td style={{ padding: '12px', fontSize: '12px', color: '#6c757d' }}>
                      {item.createdAt ? new Date(item.createdAt).toLocaleString() : 
                       item.timestamp ? new Date(item.timestamp).toLocaleString() : 'N/A'}
                    </td>
                    <td style={{ padding: '12px', fontSize: '12px', color: '#6c757d' }}>
                      {item.lastModified && item.lastModified !== 'N/A' ? new Date(item.lastModified).toLocaleString() : ''}
                    </td>
                    <td style={{ padding: '12px', textAlign: 'center' }}>
                      <button
                        onClick={async () => {
                          const sanitizedId = sanitizeId(item.id);
                          if (!sanitizedId) {
                            alert('Invalid item ID. Cannot delete this item.');
                            return;
                          }
                          
                          if (window.confirm('Are you sure you want to delete this item?')) {
                            try {
                              const response = await safeFetch('/api/items/' + encodeURIComponent(sanitizedId), {
                                method: 'DELETE'
                              });
                              const result = await response.json();
                              if (result.status === 'success') {
                                fetchItems();
                              }
                            } catch (error) {
                              console.error('Failed to delete item:', error);
                              alert('Error deleting item: ' + error.message);
                            }
                          }
                        }}
                        style={{
                          padding: '4px 8px',
                          fontSize: '12px',
                          backgroundColor: '#dc3545',
                          color: 'white',
                          border: 'none',
                          borderRadius: '3px',
                          cursor: 'pointer'
                        }}
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      
      {/* MQ Monitoring Panel */}
      {showMqPanel && (
        <div style={{
          position: 'fixed',
          top: '20px',
          right: '20px',
          width: '400px',
          height: '500px',
          backgroundColor: '#fff',
          border: '2px solid #007bff',
          borderRadius: '8px',
          boxShadow: '0 4px 8px rgba(0,0,0,0.2)',
          zIndex: 1000,
          display: 'flex',
          flexDirection: 'column'
        }}>
          <div style={{
            padding: '15px',
            backgroundColor: '#007bff',
            color: 'white',
            borderRadius: '6px 6px 0 0',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}>
            <h3 style={{ margin: 0, fontSize: '16px' }}>Amazon MQ Monitor</h3>
            <button 
              onClick={() => setShowMqPanel(false)}
              style={{
                background: 'none',
                border: 'none',
                color: 'white',
                fontSize: '18px',
                cursor: 'pointer',
                padding: '0 5px'
              }}
            >
              ×
            </button>
          </div>
          
          <div style={{ padding: '15px', borderBottom: '1px solid #dee2e6' }}>
            <div style={{ fontSize: '14px', marginBottom: '10px' }}>
              <strong>Queue Status:</strong> 
              <span style={{
                color: queueStatus?.status === 'connected' ? '#28a745' : '#dc3545',
                marginLeft: '5px'
              }}>
                {queueStatus?.status || 'unknown'}
              </span>
            </div>

            <div style={{ fontSize: '12px', color: '#6c757d', marginBottom: '10px' }}>
              📤 QUEUED: Messages sent to Amazon MQ<br/>
              📥 DEQUEUED: Messages processed by JMS listener
            </div>
            
            {queueStatus?.statistics && (
              <div style={{ 
                fontSize: '12px', 
                marginBottom: '10px',
                padding: '8px',
                backgroundColor: '#f8f9fa',
                borderRadius: '4px',
                border: '1px solid #dee2e6'
              }}>
                <div style={{ fontWeight: 'bold', marginBottom: '5px' }}>📊 Queue Statistics</div>
                <div>📤 Total Enqueued: <strong>{queueStatus.statistics.totalEnqueued}</strong></div>
                <div>📥 Total Dequeued: <strong>{queueStatus.statistics.totalDequeued}</strong></div>
                <div>💀 DLQ Count: <strong style={{color: queueStatus.statistics.totalDlqCount > 0 ? '#dc3545' : '#28a745'}}>{queueStatus.statistics.totalDlqCount || 0}</strong></div>
                <div>⏳ Pending: <strong>{Math.max(0, queueStatus.statistics.totalEnqueued - queueStatus.statistics.totalDequeued)}</strong></div>
                <div>👥 Consumers: <strong>{queueStatus.statistics.consumerCount}</strong></div>
              </div>
            )}
            <div style={{ fontSize: '12px', color: '#6c757d' }}>
              {queueStatus?.note || 'Application-level delay processing'}
            </div>
          </div>
          
          <div style={{
            flex: 1,
            padding: '15px',
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column'
          }}>
            <div style={{ 
              display: 'flex', 
              justifyContent: 'space-between', 
              alignItems: 'center',
              marginBottom: '10px'
            }}>
              <h4 style={{ margin: 0, fontSize: '14px' }}>Activity Log</h4>
              <div style={{ display: 'flex', gap: '5px' }}>
                <button 
                  onClick={() => setMqLogs([])}
                  style={{
                    padding: '4px 8px',
                    fontSize: '12px',
                    backgroundColor: '#6c757d',
                    color: 'white',
                    border: 'none',
                    borderRadius: '3px',
                    cursor: 'pointer'
                  }}
                >
                  Clear
                </button>
                <button 
                  onClick={async () => {
                    try {
                      const response = await safeFetch('/api/queue/purge', {
                        method: 'POST'
                      });
                      const result = await response.json();
                      if (result.status === 'success') {
                        setMqLogs([{
                          timestamp: new Date().toLocaleTimeString(),
                          type: 'stats',
                          message: '🧹 Queue purged - all counters reset'
                        }]);
                        fetchQueueStatus();
                      }
                    } catch (error) {
                      console.error('Failed to purge queue:', error);
                    }
                  }}
                  style={{
                    padding: '4px 8px',
                    fontSize: '12px',
                    backgroundColor: '#dc3545',
                    color: 'white',
                    border: 'none',
                    borderRadius: '3px',
                    cursor: 'pointer'
                  }}
                >
                  Purge
                </button>
              </div>
            </div>
            
            <div style={{
              flex: 1,
              overflowY: 'auto',
              fontSize: '12px',
              fontFamily: 'monospace',
              backgroundColor: '#f8f9fa',
              padding: '10px',
              borderRadius: '4px',
              border: '1px solid #dee2e6'
            }}>
              {mqLogs.length === 0 ? (
                <div style={{ color: '#6c757d', textAlign: 'center', padding: '20px' }}>
                  No activity logs yet
                </div>
              ) : (
                mqLogs.map((log, index) => {
                  const getLogStyle = (type) => {
                    switch(type) {
                      case 'queued': return { bg: '#fff3cd', border: '#ffc107', icon: '📤' };
                      case 'dequeued': return { bg: '#d1ecf1', border: '#17a2b8', icon: '📥' };
                      case 'stats': return { bg: '#e2e3e5', border: '#6c757d', icon: '📊' };
                      case 'error': return { bg: '#f8d7da', border: '#dc3545', icon: '❌' };
                      default: return { bg: '#d4edda', border: '#28a745', icon: '📊' };
                    }
                  };
                  const style = getLogStyle(log.type);
                  
                  return (
                    <div key={index} style={{
                      marginBottom: '5px',
                      padding: '8px',
                      backgroundColor: style.bg,
                      borderRadius: '4px',
                      borderLeft: '4px solid ' + style.border,
                      fontSize: '11px'
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                        <span>{style.icon}</span>
                        <span style={{ color: '#6c757d', fontSize: '10px' }}>{log.timestamp}</span>
                        <span style={{ fontWeight: 'bold' }}>{log.message}</span>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
          
          <div style={{
            padding: '10px 15px',
            borderTop: '1px solid #dee2e6',
            fontSize: '11px',
            color: '#6c757d',
            textAlign: 'center'
          }}>
            Real-time via WebSocket (DynamoDB Streams)
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
