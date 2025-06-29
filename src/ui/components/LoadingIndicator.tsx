import React, { useState, useEffect } from 'react';
import { Box, Text } from 'ink';

export const LoadingIndicator: React.FC = () => {
  const [frame, setFrame] = useState(0);
  const frames = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'];

  useEffect(() => {
    const timer = setInterval(() => {
      setFrame(prev => (prev + 1) % frames.length);
    }, 100);

    return () => clearInterval(timer);
  }, [frames.length]);

  return (
    <Box paddingX={2} paddingY={1}>
      <Text color="blue">
        {frames[frame]} Thinking...
      </Text>
    </Box>
  );
};