import { NextResponse } from 'next/server';
import { PdfUploadResponse } from '../types';

export async function POST(request: Request) {
  try {
    // 1. 클라이언트로부터 FormData 추출
    const formData = await request.formData();
    const file = formData.get('file') as File;

    if (!file) {
      return NextResponse.json(
        { error: 'No file provided' },
        { status: 400 }
      );
    }

    // 2. 파일 유효성 검사
    if (!file.type.includes('pdf')) {
      return NextResponse.json(
        { error: 'Only PDF files are allowed' },
        { status: 400 }
      );
    }

    // 3. 파일 크기 검사 (10MB)
    const maxSize = 10 * 1024 * 1024;
    if (file.size > maxSize) {
      return NextResponse.json(
        { error: 'File size exceeds 10MB limit' },
        { status: 400 }
      );
    }

    // 4. 파일을 ArrayBuffer로 변환
    const arrayBuffer = await file.arrayBuffer();
    const buffer = Buffer.from(arrayBuffer);

    // 5. 새로운 FormData 생성 (백엔드 전송용)
    const backendFormData = new FormData();
    backendFormData.append('file', new Blob([buffer], { type: file.type }), file.name);
    backendFormData.append('fileName', file.name);
    backendFormData.append('fileSize', file.size.toString());

    // 6. 백엔드 서버로 전송
    const backendUrl = process.env.BACKEND_URL;
    if (!backendUrl) {
      throw new Error('Backend URL is not configured');
    }

    const backendResponse = await fetch(`${backendUrl}/api/pdf/upload`, {
      method: 'POST',
      body: backendFormData,
    });

    // 7. 백엔드 응답 처리
    if (!backendResponse.ok) {
      const errorData = await backendResponse.json().catch(() => ({}));
      throw new Error(errorData.error || `Backend error: ${backendResponse.status}`);
    }

    // 8. 백엔드 응답을 클라이언트에 전달
    const responseData: PdfUploadResponse = await backendResponse.json();

    // 9. 성공 응답 반환
    return NextResponse.json(responseData);

  } catch (error) {
    // 10. 에러 로깅 및 응답
    console.error('Error in PDF upload:', error);
    
    return NextResponse.json(
      { 
        error: error instanceof Error ? error.message : 'Failed to upload PDF',
        timestamp: new Date().toISOString()
      },
      { status: 500 }
    );
  }
} 