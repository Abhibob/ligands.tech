import { useState, useRef } from 'react';
import { Upload, FileText, X, FileCheck } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

function getFileTypeBadge(name) {
  const ext = name.split('.').pop()?.toLowerCase();
  const map = { csv: 'CSV', json: 'JSON', txt: 'TXT', pdf: 'PDF' };
  return map[ext] || ext?.toUpperCase();
}

export default function FileUpload({ onFileSelect }) {
  const [isDragging, setIsDragging] = useState(false);
  const [file, setFile] = useState(null);
  const inputRef = useRef(null);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDragIn = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragOut = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      setFile(droppedFile);
      onFileSelect(droppedFile);
    }
  };

  const handleClick = () => inputRef.current?.click();

  const handleChange = (e) => {
    const selected = e.target.files[0];
    if (selected) {
      setFile(selected);
      onFileSelect(selected);
    }
  };

  const removeFile = (e) => {
    e.stopPropagation();
    setFile(null);
    onFileSelect(null);
  };

  return (
    <div
      onClick={handleClick}
      onDragOver={handleDrag}
      onDragEnter={handleDragIn}
      onDragLeave={handleDragOut}
      onDrop={handleDrop}
      className={`relative cursor-pointer rounded-2xl p-12 text-center transition-all duration-300 accent-top ${
        isDragging
          ? 'bg-cyan-glow/5 border border-cyan-glow'
          : file
          ? 'bg-bg-card border border-cyan-glow/30'
          : 'bg-bg-card border border-border-subtle hover:border-slate-500 hover:bg-bg-card-hover'
      }`}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".csv,.json,.txt,.pdf"
        onChange={handleChange}
        className="hidden"
      />

      <AnimatePresence mode="wait">
        {file ? (
          <motion.div
            key="file"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            className="flex flex-col items-center gap-4"
          >
            <div className="w-16 h-16 rounded-xl bg-cyan-glow/10 flex items-center justify-center">
              <FileText size={28} className="text-cyan-glow" />
            </div>
            <div>
              <div className="flex items-center justify-center gap-2 mb-1">
                <p className="text-white font-semibold text-lg">{file.name}</p>
                <span className="px-1.5 py-0.5 rounded bg-accent-blue/15 text-accent-blue text-[10px] font-mono font-bold">
                  {getFileTypeBadge(file.name)}
                </span>
              </div>
              <p className="text-slate-400 text-sm">
                {(file.size / 1024).toFixed(1)} KB
              </p>
            </div>
            {/* Loaded indicator bar */}
            <motion.div
              className="flex items-center gap-2 text-xs text-cyan-glow"
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
            >
              <FileCheck size={14} />
              <span>Ready for analysis</span>
            </motion.div>
            <button
              onClick={removeFile}
              className="flex items-center gap-1.5 text-sm text-slate-400 hover:text-red-400 transition-colors bg-transparent border-0 cursor-pointer p-0"
            >
              <X size={14} /> Remove
            </button>
          </motion.div>
        ) : (
          <motion.div
            key="empty"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex flex-col items-center gap-4"
          >
            <motion.div
              className={`w-16 h-16 rounded-xl border flex items-center justify-center transition-colors ${
                isDragging
                  ? 'bg-cyan-glow/20 border-cyan-glow'
                  : 'bg-white/5 border-border-subtle'
              }`}
              animate={isDragging ? { scale: 1.15 } : { scale: 1 }}
              transition={{ type: 'spring', stiffness: 400, damping: 15 }}
            >
              <Upload size={28} className={isDragging ? 'text-cyan-glow' : 'text-slate-400'} />
            </motion.div>
            <div>
              <p className="text-white font-medium text-lg">
                Drop your document here
              </p>
              <p className="text-slate-400 text-sm mt-1">
                or click to browse — .csv, .json, .txt, .pdf
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
