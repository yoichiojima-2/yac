import React from 'react';
import { Box, Text } from 'ink';
import { Message } from './App';
import { MessageBubble } from './MessageBubble';
import { InputField } from './InputField';
import { LoadingIndicator } from './LoadingIndicator';

interface ChatInterfaceProps {
  messages: Message[];
  currentInput: string;
  isLoading: boolean;
}

export const ChatInterface: React.FC<ChatInterfaceProps> = ({
  messages,
  currentInput,
  isLoading,
}) => {
  return (
    <Box flexDirection="column" flexGrow={1}>
      {/* Chat messages area */}
      <Box
        flexDirection="column"
        flexGrow={1}
        paddingX={1}
        paddingY={1}
      >
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}
        
        {isLoading && <LoadingIndicator />}
      </Box>
      
      {/* Input area */}
      <InputField currentInput={currentInput} />
    </Box>
  );
};