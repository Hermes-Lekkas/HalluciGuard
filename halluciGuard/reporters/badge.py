# HalluciGuard - AI Hallucination Detection Middleware
# Copyright (C) 2026 HalluciGuard Contributors

class BadgeGenerator:
    """Generates visual trust badges for AI content."""
    
    @staticmethod
    def generate_svg(trust_score: float) -> str:
        """Returns an SVG badge string based on the trust score."""
        color = "#f44336" # Red
        label = "UNTRUSTED"
        
        if trust_score >= 0.85:
            color = "#4caf50" # Green
            label = "VERIFIED"
        elif trust_score >= 0.65:
            color = "#ff9800" # Orange
            label = "MODERATE"
            
        percentage = int(trust_score * 100)
        
        svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="180" height="20">
  <linearGradient id="b" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <mask id="a">
    <rect width="180" height="20" rx="3" fill="#fff"/>
  </mask>
  <g mask="url(#a)">
    <path fill="#555" d="M0 0h110v20H0z"/>
    <path fill="{color}" d="M110 0h70v20H110z"/>
    <path fill="url(#b)" d="M0 0h180v20H0z"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="DejaVu Sans,Verdana,Geneva,sans-serif" font-size="11">
    <text x="55" y="15" fill="#010101" fill-opacity=".3">HalluciGuard</text>
    <text x="55" y="14">HalluciGuard</text>
    <text x="145" y="15" fill="#010101" fill-opacity=".3">{label} {percentage}%</text>
    <text x="145" y="14">{label} {percentage}%</text>
  </g>
</svg>"""
        return svg
