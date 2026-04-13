import SuggestionCard from '../components/SuggestionCard'
import ModeToggle from '../components/ModeToggle'
import { 
  Image, 
  Music, 
  HelpCircle, 
  Sun, 
  PenTool,
  Activity
} from 'lucide-react'

const suggestions = [
  { icon: Image, title: 'Create image', description: 'Generate visuals from text', color: 'from-indigo-500 to-indigo-600', prompt: 'Create an image concept for a futuristic city skyline at sunrise.' },
  { icon: Activity, title: 'Follow IPL', description: 'Live scores & updates', color: 'from-emerald-500 to-emerald-600', prompt: 'Give me the latest IPL scores and key match highlights.' },
  { icon: Music, title: 'Create music', description: 'AI-generated tracks', color: 'from-purple-500 to-purple-600', prompt: 'Give me a melody and rhythm concept for a high-energy cinematic track.' },
  { icon: HelpCircle, title: 'Help me learn', description: 'Tutoring & explanations', color: 'from-blue-500 to-blue-600', prompt: 'Explain transformers in simple steps with a real-world analogy.' },
  { icon: Sun, title: 'Boost my day', description: 'Motivation & insights', color: 'from-amber-500 to-amber-600', prompt: 'Give me a short, high-impact motivational plan for today.' },
  { icon: PenTool, title: 'Write anything', description: 'Drafts & copywriting', color: 'from-rose-500 to-rose-600', prompt: 'Write a polished product launch announcement for an AI app.' },
]

const HomePage = ({ onUsePrompt, userProfile }) => {
  const displayName = (userProfile?.username || userProfile?.email || 'there').trim()

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 md:py-12">
      {/* Hero Section */}
      <div className="text-center mb-9 md:mb-12">
        <h1 className="text-3xl md:text-4xl lg:text-5xl font-bold tracking-tight text-gray-900 mb-3">
          Hi {displayName},
        </h1>
        <p className="text-xl md:text-2xl text-gray-600 font-medium">
          where should we start?
        </p>
        <p className="text-gray-500 mt-3 max-w-lg mx-auto">
          Explore, create, or ask anything — I'm here to help.
        </p>
      </div>

      {/* Mode Toggle */}
      <div className="flex justify-center mb-10">
        <ModeToggle />
      </div>

      {/* Suggestion Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-5 mb-12">
        {suggestions.map((suggestion, idx) => (
          <div key={idx} onClick={() => onUsePrompt(suggestion.prompt)}>
            <SuggestionCard {...suggestion} />
          </div>
        ))}
      </div>

      {/* Footer Note */}
      <div className="text-center mt-12">
        <p className="text-xs text-gray-400">
          Powered by advanced AI · Responses may vary · <span className="underline cursor-pointer hover:text-gray-500">Privacy</span>
        </p>
      </div>
    </div>
  )
}

export default HomePage
