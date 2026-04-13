import { motion } from 'framer-motion'

const SuggestionCard = ({ icon: Icon, title, description, color }) => {
  return (
    <motion.button
      whileHover={{ y: -4 }}
      transition={{ type: 'spring', stiffness: 400, damping: 17 }}
      className="group relative flex flex-col items-start p-5 bg-white rounded-2xl border border-border shadow-premium-sm hover:shadow-premium-hover transition-all duration-300 text-left"
    >
      <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${color} mb-3 flex items-center justify-center shadow-sm`}>
        <Icon size={18} className="text-white" />
      </div>
      <h3 className="font-semibold text-gray-800 mb-1 group-hover:text-accent-600 transition-colors">
        {title}
      </h3>
      <p className="text-xs text-gray-500">{description}</p>
    </motion.button>
  )
}

export default SuggestionCard
