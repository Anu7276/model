import re

with open('c:/Users/Anurag/OneDrive/Pictures/models 2.0/web_app/templates/recommendations.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Insert style.css link
content = content.replace(
    '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">',
    '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">\n    <link rel="stylesheet" href="{{ url_for(\'static\', filename=\'style.css\') }}">'
)

# 2. Replace CSS Variables & Globals
css_target_start = """        :root {"""
css_target_end = """        /* Removed animated background orbs and noise texture for clinical look */"""

# Regex replacement
pattern = re.compile(re.escape(css_target_start) + r'.*?' + re.escape(css_target_end), re.DOTALL)

new_css = """        :root {
            /* Map specific tokens to style.css */
            --bg-deep: var(--base-dark);
            --bg-primary: var(--base-slate);
            --bg-card: var(--base-slate);
            --bg-card-hover: var(--base-surface);
            --glass-border: var(--base-border);
            --glass-border-hover: color-mix(in srgb, var(--brand-primary) 35%, var(--base-border));
            --accent-teal: var(--brand-primary);
            --accent-teal-glow: var(--brand-glow);
            --accent-purple: var(--brand-secondary);
            --accent-purple-glow: var(--brand-glow);
            --accent-blue: var(--brand-accent);
            --accent-amber: var(--status-warning);
            --shadow-card: var(--panel-shadow);
            --shadow-card-hover: var(--panel-shadow-hover);
            --shadow-glow-teal: 0 0 30px rgba(15, 82, 186, 0.12);
            --shadow-glow-purple: 0 0 30px rgba(0, 118, 206, 0.12);
        }

        body.dark-mode {
            --shadow-glow-teal: 0 0 30px rgba(59, 130, 246, 0.22);
            --shadow-glow-purple: 0 0 30px rgba(96, 165, 250, 0.22);
        }

        html { scroll-behavior: smooth; }"""

content = pattern.sub(new_css, content)

# 3. Insert body theme initialization script
body_target = """<body class="dark-mode">"""
body_replacement = """<body class="dark-mode">
    <script>
        // Sync Theme from localStorage immediately to avoid UI flash
        if (localStorage.getItem('theme') === 'light') {
            document.body.classList.remove('dark-mode');
        }
    </script>"""
content = content.replace(body_target, body_replacement)

# 4. Update the Top NavBar
nav_target = """        <!-- Sticky Top Bar -->
        <div class="rec-topbar">
            <a href="/" class="back-link">
                <i class="fas fa-arrow-left"></i> Back to Dashboard
            </a>
            <div style="display: flex; align-items: center; gap: 8px;">
                <img src="{{ url_for('static', filename='logo.png') }}" alt="Logo" style="height: 48px; width: auto; margin-left: -4px;">
                <span class="topbar-brand" style="margin: 0;">PreventAI™ Wellness</span>
            </div>
        </div>"""

nav_replace = """        <!-- Theme-aligned Top Navigation -->
        <div class="top-nav" style="position: sticky; z-index: 100;">
            <div class="logo">
                <img src="{{ url_for('static', filename='logo.png') }}" class="brand-logo" alt="PreventAI Logo">
                <span class="logo-text">PreventAI Wellness</span>
            </div>
            <div class="nav-actions">
                <a href="/" class="back-link btn-predict btn-sm" style="text-decoration: none; display: flex; align-items: center; gap: 8px;">
                    <i class="fas fa-arrow-left"></i> Dashboard
                </a>
            </div>
        </div>"""

content = content.replace(nav_target, nav_replace)

with open('c:/Users/Anurag/OneDrive/Pictures/models 2.0/web_app/templates/recommendations.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Recommendations.html updated successfully!")
