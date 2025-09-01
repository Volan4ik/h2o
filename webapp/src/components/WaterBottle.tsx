import React from "react";

interface WaterBottleProps {
  currentWater: number;
  totalGoal: number;
}

export function WaterBottle({ currentWater, totalGoal }: WaterBottleProps) {
  // процент заполнения
  const waterPercentage = Math.min((currentWater / totalGoal) * 100, 100);
  const waterHeight = (waterPercentage / 100) * 230;
  const waterY = 290 - waterHeight;

  return (
    <div className="relative flex items-center justify-center">
      <svg
        width="200"
        height="300"
        viewBox="0 0 200 300"
        className="drop-shadow-lg"
      >
        <defs>
          {/* форма бутылки */}
          <clipPath id="bottleClip">
            <path d="M65 45 L65 25 Q65 15 75 15 L125 15 Q135 15 135 25 L135 45 Q140 50 140 55 L140 275 Q140 285 130 285 L70 285 Q60 285 60 275 L60 55 Q60 50 65 45 Z" />
          </clipPath>

          {/* градиент воды */}
          <linearGradient id="waterGradient" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#87CEEB" />
            <stop offset="30%" stopColor="#60A5FA" />
            <stop offset="70%" stopColor="#3B82F6" />
            <stop offset="100%" stopColor="#1E40AF" />
          </linearGradient>

          {/* градиент бутылки */}
          <linearGradient id="bottleGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#F8FAFC" />
            <stop offset="50%" stopColor="#FFFFFF" />
            <stop offset="100%" stopColor="#F1F5F9" />
          </linearGradient>

          {/* тень бутылки */}
          <linearGradient id="bottleShadow" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#E2E8F0" />
            <stop offset="100%" stopColor="#CBD5E1" />
          </linearGradient>
        </defs>

        {/* тень бутылки */}
        <path
          d="M65 45 L65 25 Q65 15 75 15 L125 15 Q135 15 135 25 L135 45 Q140 50 140 55 L140 275 Q140 285 130 285 L70 285 Q60 285 60 275 L60 55 Q60 50 65 45 Z"
          fill="url(#bottleShadow)"
          stroke="#CBD5E1"
          strokeWidth="1"
          transform="translate(2, 2)"
          opacity="0.3"
        />

        {/* основная бутылка */}
        <path
          d="M65 45 L65 25 Q65 15 75 15 L125 15 Q135 15 135 25 L135 45 Q140 50 140 55 L140 275 Q140 285 130 285 L70 285 Q60 285 60 275 L60 55 Q60 50 65 45 Z"
          fill="url(#bottleGradient)"
          stroke="#D1D5DB"
          strokeWidth="2"
        />

        {/* внутренняя тень */}
        <path
          d="M70 20 L70 50 L65 55 L65 275 L70 280 L130 280 L135 275 L135 55 L130 50 L130 20 Z"
          fill="none"
          stroke="#E5E7EB"
          strokeWidth="1"
          opacity="0.5"
        />

        {/* вода */}
        {waterPercentage > 0 && (
          <rect
            x="60"
            y={waterY}
            width="80"
            height={waterHeight}
            fill="url(#waterGradient)"
            clipPath="url(#bottleClip)"
            className="transition-all duration-1000 ease-out"
          />
        )}

        {/* поверхность воды с бликом */}
        {waterPercentage > 0 && (
          <>
            <ellipse
              cx="100"
              cy={waterY}
              rx="38"
              ry="4"
              fill="rgba(135, 206, 235, 0.8)"
              clipPath="url(#bottleClip)"
            />
            <ellipse
              cx="100"
              cy={waterY}
              rx="30"
              ry="2"
              fill="rgba(255, 255, 255, 0.6)"
              clipPath="url(#bottleClip)"
            />
          </>
        )}

        {/* пузырьки с анимацией */}
        {waterPercentage > 10 && (
          <>
            <circle
              cx="85"
              cy={waterY + 60}
              r="1.5"
              fill="rgba(255,255,255,0.8)"
              clipPath="url(#bottleClip)"
            >
              <animate
                attributeName="cy"
                from={waterY + 60}
                to={waterY + 5}
                dur="2.5s"
                repeatCount="indefinite"
              />
              <animate
                attributeName="opacity"
                values="0.8;0"
                dur="2.5s"
                repeatCount="indefinite"
              />
            </circle>

            <circle
              cx="105"
              cy={waterY + 80}
              r="1"
              fill="rgba(255,255,255,0.6)"
              clipPath="url(#bottleClip)"
            >
              <animate
                attributeName="cy"
                from={waterY + 80}
                to={waterY + 10}
                dur="3.5s"
                repeatCount="indefinite"
              />
              <animate
                attributeName="opacity"
                values="0.6;0"
                dur="3.5s"
                repeatCount="indefinite"
              />
            </circle>

            <circle
              cx="115"
              cy={waterY + 70}
              r="1.2"
              fill="rgba(255,255,255,0.7)"
              clipPath="url(#bottleClip)"
            >
              <animate
                attributeName="cy"
                from={waterY + 70}
                to={waterY + 8}
                dur="4s"
                repeatCount="indefinite"
              />
              <animate
                attributeName="opacity"
                values="0.7;0"
                dur="4s"
                repeatCount="indefinite"
              />
            </circle>

            <circle
              cx="90"
              cy={waterY + 90}
              r="0.8"
              fill="rgba(255,255,255,0.5)"
              clipPath="url(#bottleClip)"
            >
              <animate
                attributeName="cy"
                from={waterY + 90}
                to={waterY + 12}
                dur="3s"
                repeatCount="indefinite"
              />
              <animate
                attributeName="opacity"
                values="0.5;0"
                dur="3s"
                repeatCount="indefinite"
              />
            </circle>
          </>
        )}

        {/* крышка с деталями */}
        <rect
          x="75"
          y="5"
          width="50"
          height="18"
          rx="9"
          fill="#4B5563"
          stroke="#374151"
          strokeWidth="1"
        />
        <rect x="80" y="8" width="40" height="3" rx="1.5" fill="#6B7280" />
        <rect x="80" y="13" width="40" height="2" rx="1" fill="#6B7280" />
        <rect x="80" y="16" width="40" height="2" rx="1" fill="#6B7280" />
        
        {/* блик на крышке */}
        <rect
          x="80"
          y="7"
          width="15"
          height="1"
          rx="0.5"
          fill="rgba(255,255,255,0.3)"
        />
      </svg>

      {/* индикатор процента */}
      <div className="absolute bottom-8 left-1/2 transform -translate-x-1/2 text-center">
        <div className="bg-white/95 backdrop-blur-sm rounded-lg px-3 py-1 shadow-lg border border-gray-200">
          <p className="text-sm font-medium text-gray-700">{Math.round(waterPercentage)}%</p>
        </div>
      </div>
    </div>
  );
}