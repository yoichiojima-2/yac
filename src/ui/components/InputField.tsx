import React from 'react';
import { Box, Text } from 'ink';

interface InputFieldProps {
  currentInput: string;
}

export const InputField: React.FC<InputFieldProps> = ({ currentInput }) => {
  return (
    <Box
      borderStyle="single"
      borderColor="cyan"
      paddingX={1}
      paddingY={0}
    >
      <Text color="cyan" bold>❯ </Text>
      <Text>{currentInput}</Text>
      <Text color="cyan">▋</Text>
    </Box>
  );
};