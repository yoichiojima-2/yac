import React from 'react';
import { Box, Text } from 'ink';
import { Message } from './App';

interface MessageBubbleProps {
  message: Message;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const getMessageStyle = () => {
    switch (message.type) {
      case 'user':
        return {
          color: 'blue' as const,
          prefix: '❯ ',
          borderColor: 'blue' as const,
        };
      case 'assistant':
        return {
          color: 'green' as const,
          prefix: '◐ ',
          borderColor: 'green' as const,
        };
      case 'system':
        return {
          color: 'yellow' as const,
          prefix: '◈ ',
          borderColor: 'yellow' as const,
        };
      default:
        return {
          color: 'white' as const,
          prefix: '• ',
          borderColor: 'white' as const,
        };
    }
  };

  const style = getMessageStyle();
  const timeStr = message.timestamp.toLocaleTimeString('en-US', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
  });

  return (
    <Box
      marginY={1}
      borderStyle="round"
      borderColor={style.borderColor}
      paddingX={2}
      paddingY={1}
      flexDirection="column"
    >
      <Box justifyContent="space-between" marginBottom={1}>
        <Box>
          <Text color={style.color} bold>
            {style.prefix}
            {message.type === 'user' ? 'You' : 
             message.type === 'assistant' ? 'Assistant' : 'System'}
          </Text>
        </Box>
        <Text color="gray" dimColor>
          {timeStr}
        </Text>
      </Box>
      
      <Text wrap="wrap">
        {message.content}
      </Text>
    </Box>
  );
};