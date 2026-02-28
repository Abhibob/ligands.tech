import { motion } from 'framer-motion';

export default function StepIndicator({ steps }) {
  return (
    <div className="flex items-center justify-center gap-0">
      {steps.map((step, i) => (
        <div key={i} className="flex items-center">
          {/* Dot */}
          <div className="relative flex flex-col items-center">
            <motion.div
              className="w-3.5 h-3.5 rounded-full border-2 flex items-center justify-center"
              animate={{
                borderColor: step.complete ? '#06d6a0' : '#1e2d45',
                backgroundColor: step.complete ? '#06d6a0' : 'transparent',
              }}
              transition={{ type: 'spring', stiffness: 400, damping: 20 }}
            >
              {step.complete && (
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ type: 'spring', stiffness: 500, damping: 15 }}
                  className="w-1.5 h-1.5 rounded-full bg-[#0a0e17]"
                />
              )}
            </motion.div>
            <span className="absolute top-5 text-[10px] text-slate-500 whitespace-nowrap font-medium">
              {step.label}
            </span>
          </div>
          {/* Connecting line (not after last) */}
          {i < steps.length - 1 && (
            <motion.div
              className="h-0.5 rounded-full"
              style={{ width: 48 }}
              animate={{
                backgroundColor: step.complete ? '#06d6a0' : '#1e2d45',
              }}
              transition={{ duration: 0.4 }}
            />
          )}
        </div>
      ))}
    </div>
  );
}
