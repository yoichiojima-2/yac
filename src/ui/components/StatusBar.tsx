import React from 'react';
import { Box, Text } from 'ink';

interface StatusBarProps {
  serverCount: number;
  showSidebar: boolean;
}

export const StatusBar: React.FC<StatusBarProps> = ({ serverCount, showSidebar }) => {
  return (
    <Box
      borderStyle="single"
      borderColor="gray"
      paddingX={1}
      justifyContent="space-between"
    >
      <Box>
        <Text color="green">●</Text>
        <Text color="gray"> {serverCount} servers connected</Text>
      </Box>
      
      <Box>
        <Text color="gray">
          {showSidebar ? 'Ctrl+B: Hide sidebar' : 'Ctrl+B: Show sidebar'} • Ctrl+C: Exit
        </Text>
      </Box>
    </Box>
  );
};