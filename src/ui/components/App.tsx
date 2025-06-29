import React, { useState, useEffect } from 'react';
import { Box, Text, useInput, useApp } from 'ink';
import { Header } from './Header';
import { Sidebar } from './Sidebar';
import { ChatInterface } from './ChatInterface';
import { StatusBar } from './StatusBar';
import { PythonBridge, PythonMessage, PythonStatus } from '../bridge/PythonBridge';

export interface Message {
  id: string;
  type: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  thinking?: boolean;
}

export interface AppState {
  messages: Message[];
  currentInput: string;
  isLoading: boolean;
  connectedServers: string[];
  currentModel: string;
  showSidebar: boolean;
}

export const App: React.FC = () => {
  const { exit } = useApp();
  const [state, setState] = useState<AppState>({
    messages: [
      {
        id: '1',
        type: 'system',
        content: 'Connecting to Yet Claude Code backend...',
        timestamp: new Date(),
      }
    ],
    currentInput: '',
    isLoading: true,
    connectedServers: [],
    currentModel: 'loading...',
    showSidebar: true,
  });

  const [bridge] = useState(() => new PythonBridge());
  const [connected, setConnected] = useState(false);

  // Initialize connection to Python backend
  useEffect(() => {
    const initializeBridge = async () => {
      try {
        // Set up event listeners
        bridge.on('connected', () => {
          setConnected(true);
          setState(prev => ({
            ...prev,
            messages: [
              ...prev.messages,
              {
                id: 'connected',
                type: 'system',
                content: 'Connected to Yet Claude Code! Ready to assist you.',
                timestamp: new Date(),
              }
            ],
            isLoading: false,
          }));
        });

        bridge.on('message', (message: PythonMessage) => {
          setState(prev => ({
            ...prev,
            messages: [...prev.messages, {
              id: message.id,
              type: message.type as 'user' | 'assistant' | 'system',
              content: message.content,
              timestamp: message.timestamp,
              thinking: message.thinking,
            }],
          }));
        });

        bridge.on('status', (status: PythonStatus) => {
          setState(prev => ({
            ...prev,
            connectedServers: status.connected_servers,
            currentModel: status.current_model,
            isLoading: status.loading || !!status.tool_executing,
          }));
        });

        bridge.on('tool_start', (data: any) => {
          setState(prev => ({
            ...prev,
            messages: [...prev.messages, {
              id: `tool_${Date.now()}`,
              type: 'system',
              content: `🔧 Executing ${data.tool_name}...`,
              timestamp: new Date(),
            }],
            isLoading: true,
          }));
        });

        bridge.on('tool_result', (data: any) => {
          setState(prev => ({
            ...prev,
            messages: [...prev.messages, {
              id: `tool_result_${Date.now()}`,
              type: 'system', 
              content: `✅ ${data.tool_name}: ${data.result}`,
              timestamp: new Date(),
            }],
          }));
        });

        bridge.on('error', (error: string) => {
          setState(prev => ({
            ...prev,
            messages: [...prev.messages, {
              id: `error_${Date.now()}`,
              type: 'system',
              content: `❌ Error: ${error}`,
              timestamp: new Date(),
            }],
            isLoading: false,
          }));
        });

        bridge.on('disconnect', () => {
          setConnected(false);
          setState(prev => ({
            ...prev,
            messages: [...prev.messages, {
              id: `disconnect_${Date.now()}`,
              type: 'system',
              content: '⚠️  Disconnected from backend',
              timestamp: new Date(),
            }],
            isLoading: false,
          }));
        });

        // Connect to Python backend
        await bridge.connect();
      } catch (error) {
        setState(prev => ({
          ...prev,
          messages: [...prev.messages, {
            id: `connection_error_${Date.now()}`,
            type: 'system',
            content: `❌ Failed to connect to Python backend: ${error}`,
            timestamp: new Date(),
          }],
          isLoading: false,
        }));
      }
    };

    initializeBridge();

    // Cleanup on unmount
    return () => {
      bridge.disconnect();
    };
  }, [bridge]);

  useInput((input, key) => {
    if (key.ctrl && input === 'c') {
      exit();
      return;
    }

    if (key.ctrl && input === 'b') {
      setState(prev => ({ ...prev, showSidebar: !prev.showSidebar }));
      return;
    }

    if (key.return) {
      if (state.currentInput.trim()) {
        handleSendMessage(state.currentInput.trim());
        setState(prev => ({ ...prev, currentInput: '' }));
      }
      return;
    }

    if (key.backspace || key.delete) {
      setState(prev => ({
        ...prev,
        currentInput: prev.currentInput.slice(0, -1)
      }));
      return;
    }

    if (input && !key.ctrl && !key.meta) {
      setState(prev => ({
        ...prev,
        currentInput: prev.currentInput + input
      }));
    }
  });

  const handleSendMessage = async (content: string) => {
    if (!connected || !bridge.isConnected()) {
      setState(prev => ({
        ...prev,
        messages: [...prev.messages, {
          id: `error_${Date.now()}`,
          type: 'system',
          content: '❌ Not connected to backend. Please wait for connection.',
          timestamp: new Date(),
        }],
      }));
      return;
    }

    try {
      // Send message to Python backend
      if (content.startsWith('/')) {
        await bridge.sendCommand(content);
      } else {
        await bridge.sendMessage(content);
      }
    } catch (error) {
      setState(prev => ({
        ...prev,
        messages: [...prev.messages, {
          id: `send_error_${Date.now()}`,
          type: 'system',
          content: `❌ Error sending message: ${error}`,
          timestamp: new Date(),
        }],
      }));
    }
  };

  return (
    <Box flexDirection="column" height="100%">
      <Header model={state.currentModel} />
      
      <Box flexGrow={1} flexDirection="row">
        {state.showSidebar && (
          <Sidebar 
            servers={state.connectedServers}
            width={25}
          />
        )}
        
        <ChatInterface
          messages={state.messages}
          currentInput={state.currentInput}
          isLoading={state.isLoading}
        />
      </Box>
      
      <StatusBar 
        serverCount={state.connectedServers.length}
        showSidebar={state.showSidebar}
      />
    </Box>
  );
};