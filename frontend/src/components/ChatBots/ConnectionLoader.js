import React from 'react';
import { motion } from 'framer-motion';

const ConnectionLoader = ({ isVisible, message }) => {
  if (!isVisible) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
      className="flex justify-center items-center py-6"
    >
      <div className="bg-[#36393F] px-6 py-4 rounded-lg border border-[#42464D] shadow-lg">
        <div className="flex items-center space-x-4">
          <div className="relative h-6 w-6">
            <motion.div
              animate={{ rotate: 360 }}
              transition={{
                duration: 1.5,
                repeat: Infinity,
                ease: 'linear',
              }}
              className="h-6 w-6 rounded-full border-2 border-t-indigo-500 border-r-indigo-500 border-b-[#4F545C] border-l-[#4F545C]"
            />
          </div>

          <div className="text-white font-medium">
            {message || 'Connecting'}
            <motion.span
              animate={{ opacity: [0, 1, 0] }}
              transition={{
                duration: 1.5,
                repeat: Infinity,
                times: [0, 0.5, 1],
                repeatDelay: 0.1,
              }}
            >
              ...
            </motion.span>
          </div>
        </div>
      </div>
    </motion.div>
  );
};

export default ConnectionLoader;
