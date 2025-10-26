"""
WhatsApp-inspired dark theme color palette for AutomateWhat application.
"""

class WhatsAppTheme:
    """WhatsApp-inspired dark theme with professional color palette."""
    
    # Primary WhatsApp Colors
    WHATSAPP_GREEN = "#00A884"      # Main WhatsApp green
    WHATSAPP_DARK_GREEN = "#008069" # Darker green for accents
    WHATSAPP_LIGHT_GREEN = "#25D366" # Light green for highlights
    
    # Background Colors
    DARK_BG_PRIMARY = "#111B21"     # Main dark background
    DARK_BG_SECONDARY = "#202C33"  # Secondary dark background
    DARK_BG_TERTIARY = "#2A3942"   # Tertiary dark background
    
    # Text Colors
    TEXT_PRIMARY = "#E9EDEF"        # Primary text (white-ish)
    TEXT_SECONDARY = "#8696A0"      # Secondary text (gray)
    TEXT_TERTIARY = "#667781"       # Tertiary text (darker gray)
    
    # Accent Colors
    ACCENT_BLUE = "#53BDEB"         # Blue for links/buttons
    ACCENT_RED = "#F15C6D"          # Red for errors/warnings
    ACCENT_ORANGE = "#FFA726"       # Orange for warnings
    ACCENT_PURPLE = "#AB47BC"       # Purple for special actions
    
    # Border and Divider Colors
    BORDER_PRIMARY = "#3B4A54"      # Primary borders
    BORDER_SECONDARY = "#2A3942"    # Secondary borders
    DIVIDER = "#3B4A54"            # Dividers
    
    # Status Colors
    SUCCESS = "#4CAF50"            # Success messages
    WARNING = "#FF9800"            # Warning messages
    ERROR = "#F44336"              # Error messages
    INFO = "#2196F3"               # Info messages
    
    # Chat Bubble Colors (for message display)
    BUBBLE_YOU = "#005C4B"         # Your messages (dark green)
    BUBBLE_OTHER = "#202C33"       # Other person's messages
    BUBBLE_TEXT_YOU = "#E9EDEF"    # Text in your bubbles
    BUBBLE_TEXT_OTHER = "#E9EDEF"  # Text in other bubbles
    
    @classmethod
    def get_theme_colors(cls):
        """Get complete theme color dictionary."""
        return {
            # Backgrounds
            'bg_primary': cls.DARK_BG_PRIMARY,
            'bg_secondary': cls.DARK_BG_SECONDARY,
            'bg_tertiary': cls.DARK_BG_TERTIARY,
            
            # Text
            'text_primary': cls.TEXT_PRIMARY,
            'text_secondary': cls.TEXT_SECONDARY,
            'text_tertiary': cls.TEXT_TERTIARY,
            
            # WhatsApp Brand Colors
            'whatsapp_green': cls.WHATSAPP_GREEN,
            'whatsapp_dark_green': cls.WHATSAPP_DARK_GREEN,
            'whatsapp_light_green': cls.WHATSAPP_LIGHT_GREEN,
            
            # Accents
            'accent_blue': cls.ACCENT_BLUE,
            'accent_red': cls.ACCENT_RED,
            'accent_orange': cls.ACCENT_ORANGE,
            'accent_purple': cls.ACCENT_PURPLE,
            
            # Borders
            'border_primary': cls.BORDER_PRIMARY,
            'border_secondary': cls.BORDER_SECONDARY,
            'divider': cls.DIVIDER,
            
            # Status
            'success': cls.SUCCESS,
            'warning': cls.WARNING,
            'error': cls.ERROR,
            'info': cls.INFO,
            
            # Chat Bubbles
            'bubble_you': cls.BUBBLE_YOU,
            'bubble_other': cls.BUBBLE_OTHER,
            'bubble_text_you': cls.BUBBLE_TEXT_YOU,
            'bubble_text_other': cls.BUBBLE_TEXT_OTHER,
        }
    
    @classmethod
    def get_button_styles(cls):
        """Get button style configurations."""
        return {
            'primary': {
                'bg': cls.WHATSAPP_GREEN,
                'fg': cls.TEXT_PRIMARY,
                'active_bg': cls.WHATSAPP_DARK_GREEN,
                'hover_bg': cls.WHATSAPP_LIGHT_GREEN,
            },
            'secondary': {
                'bg': cls.DARK_BG_SECONDARY,
                'fg': cls.TEXT_PRIMARY,
                'active_bg': cls.DARK_BG_TERTIARY,
                'hover_bg': cls.BORDER_PRIMARY,
            },
            'danger': {
                'bg': cls.ACCENT_RED,
                'fg': cls.TEXT_PRIMARY,
                'active_bg': '#D32F2F',
                'hover_bg': '#F44336',
            },
            'success': {
                'bg': cls.SUCCESS,
                'fg': cls.TEXT_PRIMARY,
                'active_bg': '#388E3C',
                'hover_bg': '#4CAF50',
            }
        }
    
    @classmethod
    def get_panel_styles(cls):
        """Get panel style configurations."""
        return {
            'main_panel': {
                'bg': cls.DARK_BG_PRIMARY,
                'border': cls.BORDER_PRIMARY,
            },
            'control_panel': {
                'bg': cls.DARK_BG_SECONDARY,
                'border': cls.BORDER_SECONDARY,
            },
            'preview_panel': {
                'bg': cls.DARK_BG_TERTIARY,
                'border': cls.BORDER_PRIMARY,
            },
            'response_panel': {
                'bg': cls.DARK_BG_SECONDARY,
                'border': cls.BORDER_SECONDARY,
            }
        }
