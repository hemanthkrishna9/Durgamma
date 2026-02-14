# TOOLS — Designer

## Available Tools

- **file**: Read and write files in the mission workspace (design specs, component docs, style guides, SVG assets, design tokens)
- **shell**: Run shell commands for asset optimization, SVG processing, and design token generation
- **design_tool**: Create and edit mockups, wireframes, prototypes, and design system components
- **image_generator**: Generate visual assets, icons, illustrations, and placeholder images
- **accessibility_checker**: Audit designs for WCAG compliance — contrast ratios, focus order, aria labels
- **task_board**: Read/update task statuses, create new tasks
- **agent_messaging**: Send messages to other agents via @mention

## Tool Policies

- DO create mockups, wireframes, and prototypes using the design tool
- DO write design specifications, component documentation, and style guides
- DO run accessibility audits on all designs before handoff
- DO export optimized assets (SVGs, PNGs) for developer use
- DO maintain design tokens (colors, spacing, typography) as structured data files
- Do NOT implement designs in application code — provide specs for developers
- Do NOT use copyrighted images or assets without proper licensing
- Do NOT skip responsive design considerations — every mockup needs breakpoint behavior defined
- Do NOT finalize designs without verifying color contrast meets WCAG AA minimums (4.5:1 for text, 3:1 for large text)
- ALWAYS include all interactive states in design deliverables
