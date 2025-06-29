import React from 'react';
import { Box, Text } from 'ink';

interface HeaderProps {
  model: string;
}

export const Header: React.FC<HeaderProps> = ({ model }) => {
  return (
    <Box
      borderStyle="single"
      borderColor="blue"
      paddingX={1}
      justifyContent="space-between"
    >
      <Text bold color="blue">
        Yet Claude Code
      </Text>
      <Text color="gray">
        Model: {model}
      </Text>
    </Box>
  );
};