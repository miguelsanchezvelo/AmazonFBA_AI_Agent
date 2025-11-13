/**
 * Development Disclaimer Component
 * 
 * Shows a disclaimer when data is in development or mock
 */

import React from 'react';
import { AlertCircle, Code, Wrench } from 'lucide-react';

interface DevelopmentDisclaimerProps {
  /**
   * Type of disclaimer
   */
  type?: 'development' | 'mock-data' | 'feature';
  
  /**
   * Custom message to display
   */
  message?: string;
  
  /**
   * Additional details
   */
  details?: string;
  
  /**
   * Whether to show full details expanded
   */
  expanded?: boolean;
}

export const DevelopmentDisclaimer: React.FC<DevelopmentDisclaimerProps> = ({
  type = 'development',
  message,
  details,
  expanded = false,
}) => {
  const getTypeConfig = () => {
    switch (type) {
      case 'mock-data':
        return {
          title: 'En Desarrollo - Datos de Prueba',
          defaultMessage: 'Esta sección actualmente muestra datos simulados para propósitos de demostración. Los datos reales estarán disponibles cuando se complete la integración con las fuentes de datos correspondientes.',
          icon: AlertCircle,
          bgColor: 'bg-amber-50 dark:bg-amber-950/20',
          borderColor: 'border-amber-200 dark:border-amber-800',
          textColor: 'text-amber-900 dark:text-amber-100',
          iconColor: 'text-amber-600 dark:text-amber-400',
        };
      case 'feature':
        return {
          title: 'Funcionalidad en Desarrollo',
          defaultMessage: 'Esta funcionalidad está actualmente en desarrollo y será completamente funcional en una versión futura.',
          icon: Wrench,
          bgColor: 'bg-blue-50 dark:bg-blue-950/20',
          borderColor: 'border-blue-200 dark:border-blue-800',
          textColor: 'text-blue-900 dark:text-blue-100',
          iconColor: 'text-blue-600 dark:text-blue-400',
        };
      default:
        return {
          title: 'En Desarrollo',
          defaultMessage: 'Esta sección está actualmente en desarrollo. Algunas funcionalidades pueden no estar completamente operativas.',
          icon: Code,
          bgColor: 'bg-gray-50 dark:bg-gray-950/20',
          borderColor: 'border-gray-200 dark:border-gray-800',
          textColor: 'text-gray-900 dark:text-gray-100',
          iconColor: 'text-gray-600 dark:text-gray-400',
        };
    }
  };

  const config = getTypeConfig();
  const Icon = config.icon;

  return (
    <div className={`rounded-lg border ${config.borderColor} ${config.bgColor} p-4`}>
      <div className="flex items-start gap-3">
        <Icon className={`h-5 w-5 ${config.iconColor} flex-shrink-0 mt-0.5`} />
        <div className="flex-1">
          <h4 className={`font-semibold ${config.textColor}`}>
            {config.title}
          </h4>
          <p className={`mt-1 text-sm ${config.textColor.replace('900', '800').replace('100', '200')}`}>
            {message || config.defaultMessage}
          </p>
          {details && (
            <p className={`mt-2 text-xs ${config.textColor.replace('900', '700').replace('100', '300')}`}>
              {details}
            </p>
          )}
        </div>
      </div>
    </div>
  );
};

export default DevelopmentDisclaimer;

