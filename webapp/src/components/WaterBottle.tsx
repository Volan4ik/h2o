import React from "react";

interface WaterBottleProps {
  currentWater: number;
  totalGoal: number;
}

export function WaterBottle({ currentWater, totalGoal }: WaterBottleProps) {
  // процент заполнения
  const waterPercentage = Math.min((currentWater / totalGoal) * 100, 100);
  const waterHeight = (waterPercentage / 100) * 230;
  const waterY = 280 - waterHeight;

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
            <path d="M60 40 L60 20 Q60 10 70 10 L130 10 Q140 10 140 20 L140 40 Q145 45 145 50 L145 270 Q145 280 135 280 L65 280 Q55 280 55 270 L55 50 Q55 45 60 40 Z" />
          </clipPath>

          {/* градиент воды */}
          <linearGradient id="waterGradient" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#60A5FA" />
            <stop offset="50%" stopColor="#3B82F6" />
            <stop offset="100%" stopColor="#1E40AF" />
          </linearGradient>
        </defs>

        {/* контур бутылки */}
        <path
          d="M60 40 L60 20 Q60 10 70 10 L130 10 Q140 10 140 20 L140 40 Q145 45 145 50 L145 270 Q145 280 135 280 L65 280 Q55 280 55 270 L55 50 Q55 45 60 40 Z"
          fill="rgba(255, 255, 255, 0.9)"
          stroke="#E5E7EB"
          strokeWidth="2"
        />

        {/* вода */}
        {waterPercentage > 0 && (
          <rect
            x="55"
            y={waterY}
            width="90"
            height={waterHeight}
            fill="url(#waterGradient)"
            clipPath="url(#bottleClip)"
            className="transition-all duration-1000 ease-out"
          />
        )}

        {/* поверхность воды */}
        {waterPercentage > 0 && (
          <ellipse
            cx="100"
            cy={waterY}
            rx="42"
            ry="3"
            fill="rgba(96, 165, 250, 0.6)"
            clipPath="url(#bottleClip)"
          />
        )}

        {/* пузырьки с анимацией */}
        {waterPercentage > 10 && (
          <>
            <circle
              cx="80"
              cy={waterY + 80}
              r="2"
              fill="rgba(255,255,255,0.7)"
              clipPath="url(#bottleClip)"
            >
              <animate
                attributeName="cy"
                from={waterY + 80}
                to={waterY + 10}
                dur="3s"
                repeatCount="indefinite"
              />
              <animate
                attributeName="opacity"
                values="1;0"
                dur="3s"
                repeatCount="indefinite"
              />
            </circle>

            <circle
              cx="95"
              cy={waterY + 100}
              r="1.5"
              fill="rgba(255,255,255,0.7)"
              clipPath="url(#bottleClip)"
            >
              <animate
                attributeName="cy"
                from={waterY + 100}
                to={waterY + 20}
                dur="4s"
                repeatCount="indefinite"
              />
              <animate
                attributeName="opacity"
                values="1;0"
                dur="4s"
                repeatCount="indefinite"
              />
            </circle>

            <circle
              cx="115"
              cy={waterY + 90}
              r="2"
              fill="rgba(255,255,255,0.7)"
              clipPath="url(#bottleClip)"
            >
              <animate
                attributeName="cy"
                from={waterY + 90}
                to={waterY + 15}
                dur="5s"
                repeatCount="indefinite"
              />
              <animate
                attributeName="opacity"
                values="1;0"
                dur="5s"
                repeatCount="indefinite"
              />
            </circle>
          </>
        )}

        {/* крышка */}
        <rect
          x="70"
          y="0"
          width="60"
          height="15"
          rx="7"
          fill="#6B7280"
          stroke="#4B5563"
          strokeWidth="1"
        />
        <rect x="75" y="3" width="50" height="2" rx="1" fill="#9CA3AF" />
        <rect x="75" y="7" width="50" height="2" rx="1" fill="#9CA3AF" />
      </svg>

      {/* индикатор процента */}
      <div className="absolute bottom-8 left-1/2 transform -translate-x-1/2 text-center">
        <div className="bg-white/90 backdrop-blur-sm rounded-lg px-3 py-1 shadow-md">
          <p className="text-sm text-gray-600">{Math.round(waterPercentage)}%</p>
        </div>
      </div>
    </div>
  );
}