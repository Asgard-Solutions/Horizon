# Cinematic Home controls

The user selected cinematic panels with depth, teal edges and gold details. The goal is to make the existing Home controls feel like Horizon's media center while retaining the approved two-screen layout and supplied logo/background.

Approaches considered: cinematic panels match the existing brand and provide depth without new artwork; brushed metal would make the controls feel like physical theater equipment; arcade lighting would emphasize bright glow. The user chose cinematic panels.

Use static layered dark surfaces, a restrained gold horizon accent, large Film/TV symbols on the media selectors, and Map/Compass/Search symbols on the three destination cards. Shared Sources/Settings and action buttons get matching depth and appropriate icons. Icons accompany existing labels and are hidden from accessibility names. The whole card remains one action. The informational source-status panel remains informational.

Implementation choices: use the already installed lucide-react icons and ordinary CSS gradients, borders and shadows. Use no backdrop blur, generated card artwork, extra dependencies or animation loops. Keep the existing targets, safe bounds, media scope, data, Back behavior and focus memory. A stable 4px teal inset ring and brighter surface identify actual focus; hover is quieter. No scale or translation. Compact layouts keep labels clear of icons. Honor system and app reduced-motion preferences and forced colors.

Verify the production build, existing helper tests, actual keyboard navigation and scope, normal/focused utility buttons, 1920x1080 and 1280x720, compact and manual-scale layouts. Save actual app screenshots. Existing backend services and media data are outside this styling change.
