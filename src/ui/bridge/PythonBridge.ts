import { spawn, ChildProcess } from 'child_process';
import { EventEmitter } from 'events';

export interface PythonMessage {
  type: 'message' | 'tool_execution' | 'status' | 'error' | 'system';
  id: string;
  content: string;
  timestamp: Date;
  thinking?: boolean;
  metadata?: Record<string, any>;
}

export interface PythonStatus {
  connected_servers: string[];
  current_model: string;
  loading: boolean;
  tool_executing?: string;
}

export class PythonBridge extends EventEmitter {
  private process: ChildProcess | null = null;
  private connected = false;
  private messageQueue: string[] = [];

  constructor() {
    super();
  }

  async connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        // Spawn the Python CLI in JSON API mode
        this.process = spawn('python', ['-m', 'yet_claude_code.cli.app', '--json-api'], {
          stdio: ['pipe', 'pipe', 'pipe'],
          cwd: process.cwd(),
        });

        this.process.stdout?.on('data', (data) => {
          this.handlePythonOutput(data.toString());
        });

        this.process.stderr?.on('data', (data) => {
          this.emit('error', data.toString());
        });

        this.process.on('close', (code) => {
          this.connected = false;
          this.emit('disconnect', code);
        });

        this.process.on('error', (error) => {
          this.connected = false;
          reject(error);
        });

        // Wait for connection confirmation
        this.once('connected', () => {
          this.connected = true;
          resolve();
        });

        // Timeout after 10 seconds
        setTimeout(() => {
          if (!this.connected) {
            reject(new Error('Connection timeout'));
          }
        }, 10000);

      } catch (error) {
        reject(error);
      }
    });
  }

  private handlePythonOutput(data: string): void {
    const lines = data.split('\n').filter(line => line.trim());
    
    for (const line of lines) {
      try {
        const message = JSON.parse(line);
        
        switch (message.type) {
          case 'connected':
            this.emit('connected');
            break;
          case 'status':
            this.emit('status', message.data as PythonStatus);
            break;
          case 'message':
            this.emit('message', message.data as PythonMessage);
            break;
          case 'tool_start':
            this.emit('tool_start', message.data);
            break;
          case 'tool_result':
            this.emit('tool_result', message.data);
            break;
          case 'error':
            this.emit('error', message.data);
            break;
          default:
            console.warn('Unknown message type:', message.type);
        }
      } catch (error) {
        // Ignore non-JSON output (could be startup messages)
        if (line.includes('ERROR') || line.includes('WARNING')) {
          this.emit('error', line);
        }
      }
    }
  }

  async sendMessage(content: string): Promise<void> {
    if (!this.connected || !this.process?.stdin) {
      throw new Error('Not connected to Python process');
    }

    const message = {
      type: 'user_message',
      content,
      id: Date.now().toString(),
    };

    this.process.stdin.write(JSON.stringify(message) + '\n');
  }

  async sendCommand(command: string): Promise<void> {
    if (!this.connected || !this.process?.stdin) {
      throw new Error('Not connected to Python process');
    }

    const message = {
      type: 'command',
      content: command,
      id: Date.now().toString(),
    };

    this.process.stdin.write(JSON.stringify(message) + '\n');
  }

  async getStatus(): Promise<PythonStatus> {
    return new Promise((resolve, reject) => {
      if (!this.connected || !this.process?.stdin) {
        reject(new Error('Not connected to Python process'));
        return;
      }

      const statusRequest = {
        type: 'status_request',
        id: Date.now().toString(),
      };

      // Listen for status response
      const timeout = setTimeout(() => {
        reject(new Error('Status request timeout'));
      }, 5000);

      this.once('status', (status: PythonStatus) => {
        clearTimeout(timeout);
        resolve(status);
      });

      this.process.stdin.write(JSON.stringify(statusRequest) + '\n');
    });
  }

  disconnect(): void {
    if (this.process) {
      this.process.kill();
      this.process = null;
    }
    this.connected = false;
    this.emit('disconnect');
  }

  isConnected(): boolean {
    return this.connected;
  }
}