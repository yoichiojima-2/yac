import React from 'react';
import { Box, Text } from 'ink';

interface SidebarProps {
  servers: string[];
  width: number;
}

export const Sidebar: React.FC<SidebarProps> = ({ servers, width }) => {
  return (
    <Box
      width={width}
      borderStyle="single"
      borderColor="gray"
      flexDirection="column"
      paddingX={1}
    >
      <Text bold color="green">
        MCP Servers
      </Text>
      
      <Box marginTop={1} flexDirection="column">
        {servers.map((server, index) => (
          <Box key={index} marginBottom={0}>
            <Text color="green">• </Text>
            <Text>{server}</Text>
          </Box>
        ))}
      </Box>
      
      <Box marginTop={2}>
        <Text color="gray" dimColor>
          Ctrl+B to toggle
        </Text>
      </Box>
    </Box>
  );
};