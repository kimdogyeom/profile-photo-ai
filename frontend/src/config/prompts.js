// 취업 및 프로필 사진 최적화 프롬프트 설정

export const STYLE_PROMPTS = {
  formal_interview: {
    id: 'formal_interview',
    name: '정장 면접용',
    description: '대기업/공기업 면접, 증명사진에 적합한 정통 정장 스타일',
    prompt: `Create a formal ID photo style portrait suitable for job applications and interviews. The subject must be wearing a dark navy or black formal business suit with a white or light blue dress shirt. For men, include a conservative tie. Position the subject directly facing the camera with a neutral, professional expression - slight smile is acceptable. Use a plain white or light gray background with absolutely no distractions. Apply even, frontal studio lighting that eliminates shadows on the face, similar to passport photo lighting. The framing should be a standard headshot showing head and shoulders, with the face centered and taking up about 60-70% of the frame. Ensure the photo looks clean, sharp, and suitable for official documents like resumes and job applications.`,
    icon: '👔',
    tags: ['증명사진', '면접', '이력서', '공식'],
    category: 'formal'
  },
  
  color_id_photo: {
    id: 'color_id_photo',
    name: '컬러 증명사진',
    description: '개성을 표현하는 맞춤 컬러 배경의 증명사진',
    prompt: `Create a modern ID photo with a solid, vibrant color background. The subject should be wearing a simple, neat top (like a blouse or shirt) in a color that complements the background, such as neutral tones or a contrasting color. Position the subject facing forward, with a pleasant and confident expression. Use clean, soft studio lighting that illuminates the face evenly and minimizes shadows. The background should be a single, uniform color like pastel blue, soft pink, deep green, or warm beige, without any gradients or textures. The framing should be a standard head-and-shoulders shot, suitable for modern resumes, personal branding, and social media profiles. The final image should feel stylish, contemporary, and professional.`,
    icon: '🎨',
    tags: ['컬러배경', '증명사진', '개성', '트렌디'],
    category: 'formal'
  },

  business_casual: {
    id: 'business_casual',
    name: '비즈니스 캐주얼',
    description: 'IT/스타트업, 현대적인 기업 프로필에 적합',
    prompt: `Generate a business casual portrait ideal for modern corporate environments and LinkedIn profiles. The subject should wear smart casual attire - a well-fitted blazer or cardigan over a clean shirt or blouse, in neutral or subdued colors like navy, gray, or beige. The background should be a soft-focused office environment or a clean, neutral backdrop in light gray or subtle blue. Use natural-looking studio lighting from a 45-degree angle that creates gentle shadows, adding dimension while keeping the face well-lit. The subject should have a warm, confident smile and make eye contact with the camera. Frame the shot as a professional headshot with shoulders visible, conveying approachability and competence suitable for corporate websites and professional networking platforms.`,
    icon: '💼',
    tags: ['링크드인', '회사프로필', 'IT업계', '스타트업'],
    category: 'business'
  },
  
  outdoor_professional: {
    id: 'outdoor_professional',
    name: '야외 프로필',
    description: '자연광을 활용한 부드럽고 편안한 야외 프로필',
    prompt: `Generate a professional portrait taken outdoors with beautiful natural lighting. The subject should wear smart casual or business casual attire. Position them in a pleasant outdoor setting, such as a modern urban park, against a backdrop of minimalist architecture, or with soft green foliage. The background should be tastefully blurred (bokeh effect) to keep the focus on the subject. Use the soft light of a slightly overcast day or the golden hour to create a warm, flattering glow. The subject's pose should be relaxed and natural, conveying approachability and confidence. This style is perfect for professionals who want to appear friendly and modern, such as consultants, real estate agents, or creative entrepreneurs.`,
    icon: '🌳',
    tags: ['자연광', '야외', '편안한', '네트워킹'],
    category: 'business'
  },

  warm_professional: {
    id: 'warm_professional',
    name: '친근한 전문가',
    description: '서비스직, 영업, 고객 응대 직무에 적합',
    prompt: `Create a warm and approachable professional portrait perfect for customer-facing roles and service industries. The subject should wear neat, professional attire in soft, welcoming colors - perhaps a light-colored shirt or blouse, possibly with a cardigan or jacket. The background should be warm and inviting, either a soft cream color or a gently blurred professional setting with warm lighting. Use soft, flattering lighting that creates a friendly glow, avoiding harsh shadows. The subject should have a genuine, warm smile that reaches the eyes, projecting friendliness and trustworthiness. The overall atmosphere should balance professionalism with approachability, making viewers feel comfortable and welcomed. Ideal for roles in healthcare, education, hospitality, sales, and customer service.`,
    icon: '😊',
    tags: ['서비스직', '영업', '고객응대', '친근한'],
    category: 'service'
  },
  
  announcer_lecturer: {
    id: 'announcer_lecturer',
    name: '아나운서/강사',
    description: '신뢰감을 주는 아나운서, 강사, 전문직 스타일',
    prompt: `Create a highly professional and trustworthy portrait suitable for an announcer, lecturer, or public speaker. The subject should wear professional attire, such as a sharp blazer or a sophisticated blouse in a solid, strong color like blue, gray, or white. The background must be clean and simple, either a neutral studio backdrop or a subtly blurred professional environment like a modern auditorium or office. Use bright, clear, and professional studio lighting that conveys clarity and confidence, with a key light to highlight the face and a fill light to soften shadows. The subject should have a confident, engaging expression with direct eye contact, projecting intelligence and authority. The overall image should be sharp, polished, and exude credibility.`,
    icon: '🎙️',
    tags: ['신뢰감', '전문직', '강사', '아나운서'],
    category: 'service'
  },

  creative_professional: {
    id: 'creative_professional',
    name: '크리에이티브 직군',
    description: '디자이너, 마케터, 크리에이티브 업계 프로필',
    prompt: `Generate a contemporary professional portrait suitable for creative industries like design, marketing, and media. The subject should wear stylish but professional clothing - a well-fitted shirt, modern blazer, or fashionable top in colors that complement their features. The background can be more dynamic: a modern office space with soft-focused elements, urban architecture, or a clean backdrop with subtle color accents. Use modern studio lighting techniques with a key light and subtle rim light to add depth and visual interest. The subject should appear confident and expressive, with a natural pose that shows personality while maintaining professionalism. The composition can be slightly more dynamic than traditional headshots, perhaps with the subject at a slight angle. Perfect for portfolios, agency websites, and creative industry networking.`,
    icon: '🎨',
    tags: ['디자이너', '마케터', '크리에이티브', '포트폴리오'],
    category: 'creative'
  },
  
  academic_professional: {
    id: 'academic_professional',
    name: '학술/연구직',
    description: '교수, 연구원, 학술 프로필에 적합',
    prompt: `Create a distinguished academic portrait suitable for university profiles and research institutions. The subject should wear professional but slightly relaxed attire - a blazer with or without a tie, or a professional cardigan over a collared shirt. The background should suggest an academic setting: soft-focused bookshelves, a neutral office environment, or a clean backdrop in deep blue or gray tones. Use soft, natural-looking lighting that creates a thoughtful, intellectual atmosphere. The subject should have a calm, confident expression with a subtle, genuine smile, projecting knowledge and approachability. The composition should be classic and timeless, avoiding trendy elements. Perfect for university websites, research publications, conference materials, and academic networking platforms.`,
    icon: '📚',
    tags: ['교수', '연구원', '학술', '대학'],
    category: 'academic'
  },
  
  linkedin_optimized: {
    id: 'linkedin_optimized',
    name: '링크드인 최적화',
    description: 'LinkedIn 프로필에 최적화된 현대적 스타일',
    prompt: `Generate a LinkedIn-optimized professional headshot that stands out in search results and profile views. The subject should wear business professional or smart casual attire in colors that photograph well - solid colors in jewel tones or classic neutrals work best. Position against a simple, professional background in LinkedIn's signature blue-gray tones or neutral colors that don't distract. Use professional studio lighting with a main light at 45 degrees and a fill light to minimize shadows, creating an even, polished look. The subject should face the camera directly with a confident, authentic smile and direct eye contact, projecting competence and approachability. Frame the shot showing head and shoulders with some space around the subject, following LinkedIn's recommended 400x400px minimum dimensions. The photo should be sharp, well-lit, and professional while appearing natural and personable.`,
    icon: '💻',
    tags: ['링크드인', 'SNS', '네트워킹', '온라인'],
    category: 'social'
  },
  
  passport_style: {
    id: 'passport_style',
    name: '증명사진 (여권형)',
    description: '공식 서류용 표준 증명사진',
    prompt: `Create a standard passport-style ID photo meeting official document requirements. The subject must wear formal attire with a solid-colored suit or jacket over a light-colored shirt - avoid patterns or logos. Position the subject directly facing the camera with a neutral expression, mouth closed, and eyes open looking straight ahead. Use a pure white background with no shadows or texture. Apply even, diffused frontal lighting that eliminates all shadows from the face and background, meeting biometric photo standards. The framing must show the full head and top of shoulders, with the face taking up 70-80% of the frame. Ensure the photo is sharp, well-focused, and meets the technical requirements for passports, visas, and official identification documents. The result should be a clean, professional ID photo suitable for government documents and official applications.`,
    icon: '🪪',
    tags: ['증명사진', '여권', '비자', '공식서류'],
    category: 'formal'
  },
  
  custom: {
    id: 'custom',
    name: '직접 입력',
    description: '원하는 스타일을 직접 설명해주세요',
    prompt: '',
    icon: '✏️',
    tags: ['맞춤형'],
    category: 'custom'
  }
};

// 카테고리 정의
export const STYLE_CATEGORIES = {
  formal: { name: '정장/공식', icon: '👔' },
  business: { name: '비즈니스', icon: '💼' },
  service: { name: '서비스직', icon: '😊' },
  creative: { name: '크리에이티브', icon: '🎨' },
  academic: { name: '학술/교육', icon: '📚' },
  social: { name: 'SNS/온라인', icon: '💻' },
  custom: { name: '직접 입력', icon: '✏️' }
};

// 프롬프트 작성 가이드라인
export const PROMPT_GUIDELINES = {
  title: '취업/프로필 사진 촬영 가이드',
  tips: [
    '용도를 명확히 하세요 (면접, 이력서, 회사 프로필, SNS 등)',
    '복장을 구체적으로 설명하세요 (정장, 캐주얼, 색상 등)',
    '배경은 단순하고 깔끔한 것이 좋습니다',
    '조명은 얼굴이 잘 보이도록 밝고 균일하게',
    '표정은 자연스럽고 친근하게 (약간의 미소 권장)'
  ],
  examples: [
    '좋은 예: "면접용 정장 사진이 필요합니다. 검정 정장에 흰색 셔츠를 입고, 흰색 배경에서 정면을 바라보는 증명사진 스타일로 만들어주세요."',
    '나쁜 예: "멋진 사진, 프로페셔널, 깔끔하게"'
  ],
  useCases: {
    formal_interview: ['대기업 면접', '공무원 시험', '증명사진', '이력서'],
    color_id_photo: ['개인 브랜딩', '사원증', 'SNS 프로필', '최신 이력서'],
    business_casual: ['IT 회사 면접', '스타트업', '링크드인', '회사 내부 프로필'],
    outdoor_professional: ['프리랜서', '컨설턴트', '부동산', '개인 웹사이트'],
    warm_professional: ['서비스직 이력서', '영업직', '고객 응대', '상담직'],
    announcer_lecturer: ['강사 프로필', '아나운서', '전문직', '컨퍼런스 발표자'],
    creative_professional: ['디자이너 포트폴리오', '마케터', '기획자', '광고업'],
    academic_professional: ['교수 프로필', '연구원', '학술대회', '논문 저자'],
    linkedin_optimized: ['링크드인 프로필', '온라인 네트워킹', '헤드헌팅'],
    passport_style: ['여권 사진', '비자 신청', '면허증', '학생증']
  }
};

export const getStylesList = () => Object.values(STYLE_PROMPTS);

export const getStylesByCategory = () => {
  const byCategory = {};
  Object.values(STYLE_PROMPTS).forEach(style => {
    const category = style.category || 'custom';
    if (!byCategory[category]) {
      byCategory[category] = [];
    }
    byCategory[category].push(style);
  });
  return byCategory;
};

export const getStylePrompt = (styleId, customPrompt = '') => {
  const style = STYLE_PROMPTS[styleId];
  if (!style) {
    return STYLE_PROMPTS.formal_interview.prompt;
  }
  
  if (styleId === 'custom') {
    return customPrompt || STYLE_PROMPTS.formal_interview.prompt;
  }
  
  return style.prompt;
};

// 프롬프트 개선 함수 (취업/프로필 사진 용도에 맞춰)
export const enhancePrompt = (userInput) => {
  if (!userInput || userInput.trim().length === 0) {
    return STYLE_PROMPTS.formal_interview.prompt;
  }
  
  // 이미 충분히 구체적인 프롬프트인 경우
  if (userInput.length > 100 && userInput.includes(' ') && userInput.split(' ').length > 15) {
    return userInput;
  }
  
  // 짧은 입력을 취업/프로필 사진 용도에 맞춰 개선
  return `Create a professional profile photo for job applications and career purposes with the following requirements: ${userInput}. Ensure the subject wears appropriate professional attire, uses clean and simple background, and proper studio lighting that highlights the face clearly. The composition should follow standard headshot framing suitable for resumes, LinkedIn profiles, and professional networking. The final photo should look polished, professional, and help the subject make a positive first impression to potential employers.`;
};
