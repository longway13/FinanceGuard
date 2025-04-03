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
    
    // 백엔드 API 연동 준비
    // 실제 백엔드 연동 시, 아래 코드 사용
    const backendUrl = process.env.BACKEND_API_URL || 'http://localhost:3000/api';
    const response = await fetch(`${backendUrl}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${process.env.API_KEY}`
      },
      body: JSON.stringify({ query }),
    });

    if (!response.ok) {
      throw new Error(`Backend API error: ${response.statusText}`);
    }

    const data = await response.json();

    return NextResponse.json(data);
  } catch (error) {
    console.error('Error in chat API:', error);
    return NextResponse.json(
      { error: 'Error regarding agent response about user query. Please try again.' } as ErrorResponse,
      { status: 500 }
    );
  }
} 