/**
 * AnimatedNumber Component - Smooth number transitions
 * 
 * Animates number changes with spring animation
 */

import React, { useEffect, useState } from 'react';
import { useSpring, useTransform } from 'framer-motion';

interface AnimatedNumberProps {
  value: number;
  format?: (num: number) => string;
  className?: string;
}

export const AnimatedNumber: React.FC<AnimatedNumberProps> = ({
  value,
  format = (num) => num.toString(),
  className,
}) => {
  const spring = useSpring(value, { mass: 0.8, stiffness: 75, damping: 15 });
  const display = useTransform(spring, (current) =>
    format(Math.round(current))
  );
  const [displayValue, setDisplayValue] = useState(format(value));

  useEffect(() => {
    spring.set(value);
    const unsubscribe = display.onChange((latest) => {
      setDisplayValue(latest);
    });
    return () => unsubscribe();
  }, [value, spring, display]);

  return <span className={className}>{displayValue}</span>;
};

