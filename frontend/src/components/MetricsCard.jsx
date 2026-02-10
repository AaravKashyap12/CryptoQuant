import { motion } from 'framer-motion';
import { cn } from '../lib/utils';
import { Info } from 'lucide-react';


export function MetricsCard({ title, value, subValue, trend, tooltip, className }) {
    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            whileHover={{ scale: 1.02, borderColor: '#555' }}
            transition={{ duration: 0.3 }}
            className={cn("bg-[#1e1e1e] p-6 rounded-2xl border border-[#333] transition-colors group cursor-default", className)}
        >
            <div className="flex justify-between items-start mb-2">
                <h3 className="text-gray-400 text-sm font-medium flex items-center gap-2">
                    {title}
                    {tooltip && (
                        <div className="group/tooltip relative">
                            <Info size={14} className="text-gray-600 hover:text-gray-400 cursor-help" />
                            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-48 p-2 bg-black border border-[#333] rounded-lg text-xs text-gray-300 opacity-0 group-hover/tooltip:opacity-100 transition-opacity pointer-events-none z-10 shadow-xl">
                                {tooltip}
                            </div>
                        </div>
                    )}
                </h3>
                {trend && (
                    <span className={cn(
                        "text-xs font-bold px-2 py-1 rounded-full border",
                        trend === 'up' || trend.includes('Bullish')
                            ? "bg-green-500/10 text-green-500 border-green-500/20"
                            : "bg-red-500/10 text-red-500 border-red-500/20"
                    )}>
                        {trend === 'up' || trend.includes('Bullish') ? '↗ Bullish' : '↘ Bearish'}
                    </span>
                )}
            </div>

            <div className="flex items-baseline gap-2">
                <span className="text-3xl font-bold text-white tracking-tight">{value}</span>
                {subValue && <span className="text-sm text-gray-500 font-medium">{subValue}</span>}
            </div>
        </motion.div>
    );
}
