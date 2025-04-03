import { NextRequest, NextResponse } from 'next/server';
import { ChatRequest, BackendResponse, ErrorResponse } from '@/types/chat';

// 기존 인터페이스 제거 (타입 파일로 이동됨)
// interface ChatRequest {
//   query: string;
// }

export async function POST(request: NextRequest) {
  try {
    const body: ChatRequest = await request.json();
    const { query } = body;
    
    // 인증 실패, 권한 오류 테스트 (실제 구현 시 제거 필요)
    if (query.toLowerCase().includes('권한') || query.toLowerCase().includes('인증')) {
      // 인증/권한 오류 - 메인 페이지로 리다이렉션
      return NextResponse.redirect(new URL('/', request.nextUrl.origin));
    }
    
    // 심각한 오류 테스트 (실제 구현 시 제거 필요)
    if (query.toLowerCase().includes('오류') || query.toLowerCase().includes('에러')) {
      // 심각한 오류 - 에러 페이지로 리다이렉션
      return NextResponse.redirect(new URL('/error', request.nextUrl.origin));
    }
    
    // 독소 조항 요청 테스트 - 실제 개발 시 이 로직은 백엔드에서 처리
    if (query.toLowerCase().includes('독소') || query.toLowerCase().includes('조항') || query.toLowerCase().includes('하이라이트')) {
      const mock_highlights = {
        "type": "highlights",
        "rationale": "이 금융 상품은 다양한 수수료가 복잡하게 얽혀 있으며, 일부 조항은 소비자에게 불리한 조건을 포함하고 있습니다. 특히 중도 해지, 유지 수수료, 운용 수수료가 과도하게 책정되어 있어 주의가 필요합니다.",
        "highlights": [
          "집합투자증권",
          "예금성 상품과 구별되는 특징"
        ]
      };
      
      return NextResponse.json(mock_highlights);
    }
    
    // 시뮬레이션 요청 처리
    if (query.toLowerCase().includes('시뮬레이션')) {
      const mock_simulation = {
        "type": "simulation",
        "message": "투자 상품에 대한 시물레이션 대화입니다.",
        "simulations": [
          {
            "id": 1,
            "situation": "3년 후에 투자 상품의 수익률이 기존 보장율보다 떨어짐.",
            "user": "최근 수익률을 확인해보니 보장율보다 낮던데, 이유가 뭔가요?",
            "consultant": "안녕하세요, 고객님. 시장 금리 하락 등의 영향으로 수익률이 일시적으로 보장율보다 낮게 나타날 수 있습니다. 자세한 내용을 확인해 드릴까요?"
          },
          {
            "id": 2,
            "situation": "수익률이 내가 원하는 만큼 나오지 않아서 해지하고 싶은 경우",
            "user": "기대했던 수익이 안 나와서 해지하고 싶은데, 어떻게 해야 하나요?",
            "consultant": "해지는 가능하지만, 상품에 따라 수수료나 손실이 발생할 수 있어요. 원하시면 해지 절차와 유의사항을 안내해 드릴게요."
          }
        ]
      };
      
      return NextResponse.json(mock_simulation);
    }
    
    // 백엔드 API 연동 준비
    // 실제 백엔드 연동 시, 아래 코드 사용
    const backendUrl = process.env.BACKEND_URL || 'http://0.0.0.0:5000';
    const response = await fetch(`${backendUrl}/api/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ query }),
    });

    if (!response.ok) {
      // 백엔드 응답 상태에 따른 리다이렉션
      if (response.status === 401 || response.status === 403) {
        // 인증/권한 오류 - 메인 페이지로 리다이렉션
        return NextResponse.redirect(new URL('/', request.nextUrl.origin));
      } else if (response.status >= 500) {
        // 서버 오류 - 에러 페이지로 리다이렉션
        return NextResponse.redirect(new URL('/error', request.nextUrl.origin));
      }
      throw new Error(`Backend API error: ${response.statusText}`);
    }

    const data = await response.json();

    return NextResponse.json(data);
  } catch (error) {
    console.error('Error in chat API:', error);
    
    // 심각한 오류일 경우 에러 페이지로 리다이렉션
    if ((error as Error).message.includes('Backend API error') || 
        (error as Error).message.includes('ECONNREFUSED') ||
        (error as Error).message.includes('fetch failed')) {
      return NextResponse.redirect(new URL('/error', request.nextUrl.origin));
    }
    
    return NextResponse.json(
      { error: 'Error regarding agent response about user query. Please try again.' } as ErrorResponse,
      { status: 500 }
    );
  }
} 