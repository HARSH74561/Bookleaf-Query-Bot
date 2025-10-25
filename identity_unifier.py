# identity_unifier.py - Multi-platform Identity Matching

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from fuzzywuzzy import fuzz
from thefuzz import process
import re
import json

@dataclass
class AuthorIdentity:
    """Unified author identity across platforms"""
    internal_id: str
    canonical_email: str
    canonical_name: str
    phone_numbers: List[str]
    social_handles: Dict[str, str]  # platform -> handle
    alternative_emails: List[str]
    confidence_score: float
    verification_status: str  # 'verified', 'needs_review', 'auto_matched'

class IdentityUnifier:
    """
    Advanced identity unification system that links authors
    across multiple platforms using fuzzy matching and ML
    """
    
    # Scoring weights
    WEIGHTS = {
        'email_exact': 1.0,
        'email_fuzzy': 0.7,
        'name_exact': 0.9,
        'name_fuzzy': 0.6,
        'phone': 0.95,
        'social_handle': 0.85
    }
    
    VERIFICATION_THRESHOLD = 0.85  # Auto-match above this
    REVIEW_THRESHOLD = 0.60  # Manual review between thresholds
    
    def __init__(self):
        self.unified_profiles = []  # In production, this would be a database
    
    def normalize_email(self, email: str) -> str:
        """Normalize email for comparison"""
        email = email.lower().strip()
        # Handle gmail dot notation (john.doe@gmail.com = johndoe@gmail.com)
        if '@gmail.com' in email:
            local, domain = email.split('@')
            local = local.replace('.', '')
            email = f"{local}@{domain}"
        return email
    
    def normalize_phone(self, phone: str) -> str:
        """Normalize phone number"""
        # Remove all non-digits
        phone = re.sub(r'\D', '', phone)
        # Handle Indian numbers
        if len(phone) == 10:
            phone = '91' + phone
        return phone
    
    def normalize_name(self, name: str) -> str:
        """Normalize name for comparison"""
        # Remove special characters, extra spaces
        name = re.sub(r'[^\w\s]', '', name)
        name = ' '.join(name.split())
        return name.lower().strip()
    
    def extract_social_handle(self, text: str) -> Optional[str]:
        """Extract social media handle from various formats"""
        # Remove URL parts
        text = text.replace('https://', '').replace('http://', '')
        text = text.replace('www.', '')
        text = text.replace('instagram.com/', '')
        text = text.replace('twitter.com/', '')
        text = text.replace('@', '')
        
        # Extract handle
        handle = text.split('/')[0].split('?')[0].strip()
        return handle if handle else None
    
    def calculate_name_similarity(self, name1: str, name2: str) -> float:
        """Calculate name similarity with various strategies"""
        name1 = self.normalize_name(name1)
        name2 = self.normalize_name(name2)
        
        # Exact match
        if name1 == name2:
            return 1.0
        
        # Token sort ratio (handles "Sara Johnson" vs "Johnson Sara")
        token_sort = fuzz.token_sort_ratio(name1, name2) / 100
        
        # Partial ratio (handles "Sara J." vs "Sara Johnson")
        partial = fuzz.partial_ratio(name1, name2) / 100
        
        # Check for initials match (Sara J. = Sara Johnson)
        name1_parts = name1.split()
        name2_parts = name2.split()
        
        initial_match = False
        if len(name1_parts) >= 2 and len(name2_parts) >= 2:
            # First name match + last initial
            if (name1_parts[0] == name2_parts[0] and 
                (name1_parts[-1][0] == name2_parts[-1][0] or 
                 name2_parts[-1][0] == name1_parts[-1][0])):
                initial_match = True
        
        if initial_match:
            return max(token_sort, 0.85)
        
        return max(token_sort, partial)
    
    def match_contact(
        self,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        name: Optional[str] = None,
        social_handle: Optional[str] = None,
        platform: str = 'unknown'
    ) -> Tuple[Optional[AuthorIdentity], float, str]:
        """
        Match incoming contact to existing unified profile
        
        Returns:
            (matched_profile, confidence_score, action)
            action: 'auto_match', 'needs_review', 'create_new'
        """
        
        if not self.unified_profiles:
            # No existing profiles, create new
            return None, 0.0, 'create_new'
        
        match_scores = []
        
        for profile in self.unified_profiles:
            score = 0.0
            score_breakdown = {}
            
            # Email matching
            if email:
                norm_email = self.normalize_email(email)
                
                # Check canonical email
                if norm_email == self.normalize_email(profile.canonical_email):
                    score += self.WEIGHTS['email_exact']
                    score_breakdown['email'] = 'exact'
                else:
                    # Check alternative emails
                    alt_match = any(
                        norm_email == self.normalize_email(alt_email)
                        for alt_email in profile.alternative_emails
                    )
                    if alt_match:
                        score += self.WEIGHTS['email_exact']
                        score_breakdown['email'] = 'alt_exact'
                    else:
                        # Fuzzy email match (same domain, similar local part)
                        email_similarity = fuzz.ratio(
                            norm_email.split('@')[0],
                            profile.canonical_email.split('@')[0]
                        ) / 100
                        if email_similarity > 0.8:
                            score += self.WEIGHTS['email_fuzzy'] * email_similarity
                            score_breakdown['email'] = f'fuzzy_{email_similarity:.2f}'
            
            # Phone matching
            if phone:
                norm_phone = self.normalize_phone(phone)
                for profile_phone in profile.phone_numbers:
                    if norm_phone == self.normalize_phone(profile_phone):
                        score += self.WEIGHTS['phone']
                        score_breakdown['phone'] = 'exact'
                        break
            
            # Name matching
            if name:
                name_similarity = self.calculate_name_similarity(name, profile.canonical_name)
                if name_similarity > 0.9:
                    score += self.WEIGHTS['name_exact'] * name_similarity
                    score_breakdown['name'] = f'strong_{name_similarity:.2f}'
                elif name_similarity > 0.7:
                    score += self.WEIGHTS['name_fuzzy'] * name_similarity
                    score_breakdown['name'] = f'fuzzy_{name_similarity:.2f}'
            
            # Social handle matching
            if social_handle:
                norm_handle = self.extract_social_handle(social_handle)
                if norm_handle and platform in profile.social_handles:
                    profile_handle = self.extract_social_handle(profile.social_handles[platform])
                    if norm_handle.lower() == profile_handle.lower():
                        score += self.WEIGHTS['social_handle']
                        score_breakdown['social'] = 'exact'
            
            # Normalize score (max possible score varies based on available data)
            max_possible = sum([
                self.WEIGHTS['email_exact'] if email else 0,
                self.WEIGHTS['phone'] if phone else 0,
                self.WEIGHTS['name_exact'] if name else 0,
                self.WEIGHTS['social_handle'] if social_handle else 0
            ])
            
            normalized_score = score / max_possible if max_possible > 0 else 0
            
            match_scores.append((profile, normalized_score, score_breakdown))
        
        # Get best match
        match_scores.sort(key=lambda x: x[1], reverse=True)
        best_match, confidence, breakdown = match_scores[0]
        
        # Determine action
        if confidence >= self.VERIFICATION_THRESHOLD:
            action = 'auto_match'
        elif confidence >= self.REVIEW_THRESHOLD:
            action = 'needs_review'
        else:
            action = 'create_new'
        
        print(f"Match confidence: {confidence:.2%} - {breakdown}")
        
        return best_match, confidence, action
    
    def create_unified_profile(
        self,
        email: str,
        name: str,
        phone: Optional[str] = None,
        social_handles: Optional[Dict[str, str]] = None
    ) -> AuthorIdentity:
        """Create new unified author profile"""
        import uuid
        
        profile = AuthorIdentity(
            internal_id=str(uuid.uuid4()),
            canonical_email=self.normalize_email(email),
            canonical_name=name,
            phone_numbers=[self.normalize_phone(phone)] if phone else [],
            social_handles=social_handles or {},
            alternative_emails=[],
            confidence_score=1.0,
            verification_status='verified'
        )
        
        self.unified_profiles.append(profile)
        return profile
    
    def merge_profiles(
        self,
        profile1: AuthorIdentity,
        profile2: AuthorIdentity,
        keep_profile: int = 1
    ) -> AuthorIdentity:
        """Merge two profiles (for manual review resolution)"""
        primary = profile1 if keep_profile == 1 else profile2
        secondary = profile2 if keep_profile == 1 else profile1
        
        # Merge phone numbers
        for phone in secondary.phone_numbers:
            if phone not in primary.phone_numbers:
                primary.phone_numbers.append(phone)
        
        # Merge social handles
        for platform, handle in secondary.social_handles.items():
            if platform not in primary.social_handles:
                primary.social_handles[platform] = handle
        
        # Add secondary email as alternative
        if secondary.canonical_email not in primary.alternative_emails:
            primary.alternative_emails.append(secondary.canonical_email)
        
        # Remove secondary profile
        self.unified_profiles.remove(secondary)
        
        return primary
    
    def generate_unification_report(self) -> Dict:
        """Generate report of unification system performance"""
        total = len(self.unified_profiles)
        verified = sum(1 for p in self.unified_profiles if p.verification_status == 'verified')
        needs_review = sum(1 for p in self.unified_profiles if p.verification_status == 'needs_review')
        
        return {
            'total_profiles': total,
            'verified': verified,
            'needs_review': needs_review,
            'auto_matched': total - verified - needs_review,
            'avg_confidence': sum(p.confidence_score for p in self.unified_profiles) / total if total > 0 else 0
        }

# Demo usage
def demo_identity_unification():
    """Demonstrate identity unification system"""
    unifier = IdentityUnifier()
    
    # Create initial profile
    profile1 = unifier.create_unified_profile(
        email="sara.johnson@xyz.com",
        name="Sara Johnson",
        phone="+91 9876543210",
        social_handles={"instagram": "@sarapoetry23"}
    )
    
    print("✅ Created profile:", profile1.canonical_email)
    print()
    
    # Test various matching scenarios
    test_cases = [
        {
            "description": "WhatsApp contact (phone only)",
            "data": {"phone": "9876543210", "name": None, "email": None}
        },
        {
            "description": "Instagram DM (handle + partial name)",
            "data": {"social_handle": "@sarapoetry23", "name": "Sara J.", "email": None}
        },
        {
            "description": "Email with slight variation",
            "data": {"email": "sarajohnson@xyz.com", "name": "Sara Johnson", "phone": None}
        },
        {
            "description": "Different email but same name/phone",
            "data": {"email": "sara.j@gmail.com", "name": "Sara Johnson", "phone": "+91 9876543210"}
        },
        {
            "description": "Low confidence - different person",
            "data": {"email": "john.doe@example.com", "name": "John Doe", "phone": None}
        }
    ]
    
    for test in test_cases:
        print(f"🔍 Testing: {test['description']}")
        matched, confidence, action = unifier.match_contact(**test['data'], platform='test')
        
        if matched:
            print(f"   ✅ Matched to: {matched.canonical_email}")
        else:
            print(f"   ❌ No match found")
        
        print(f"   📊 Confidence: {confidence:.2%}")
        print(f"   🎯 Action: {action}")
        print()
    
    # Generate report
    report = unifier.generate_unification_report()
    print("📈 Unification Report:")
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    demo_identity_unification()
