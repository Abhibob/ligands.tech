// Shared animation variants — prevents copy-paste sameness across pages

export const stagger = {
  container: {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: 0.08,
        delayChildren: 0.1,
      },
    },
  },
  item: {
    hidden: { opacity: 0, y: 16 },
    show: {
      opacity: 1,
      y: 0,
      transition: { type: 'spring', stiffness: 300, damping: 24 },
    },
  },
};

export const slideFromLeft = {
  hidden: { opacity: 0, x: -30 },
  show: {
    opacity: 1,
    x: 0,
    transition: { type: 'spring', stiffness: 260, damping: 20 },
  },
};

export const slideFromRight = {
  hidden: { opacity: 0, x: 30 },
  show: {
    opacity: 1,
    x: 0,
    transition: { type: 'spring', stiffness: 260, damping: 20 },
  },
};

export const scaleIn = {
  hidden: { opacity: 0, scale: 0.85 },
  show: {
    opacity: 1,
    scale: 1,
    transition: { type: 'spring', stiffness: 350, damping: 22 },
  },
};

export const fadeIn = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { duration: 0.5 },
  },
};

// Alternating left/right entrance for table rows
export function tableRow(index) {
  const isEven = index % 2 === 0;
  return {
    hidden: { opacity: 0, x: isEven ? -12 : 12 },
    show: {
      opacity: 1,
      x: 0,
      transition: {
        type: 'spring',
        stiffness: 280,
        damping: 22,
        delay: index * 0.04,
      },
    },
  };
}
