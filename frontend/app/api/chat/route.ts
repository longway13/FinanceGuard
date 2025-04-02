import { NextResponse } from 'next/server';
import { ChatRequest, ChatResponse } from '../types';

export async function POST(request: Request) {
  try {
    const body: ChatRequest = await request.json();
    const { query } = body;

    // TODO: Implement actual API call to backend
    const response = await fetch(`${process.env.BACKEND_URL}/api/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ query }),
    });

    if (!response.ok) {
      throw new Error('Failed to get chat response');
    }

    const data: ChatResponse = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error in chat API:', error);
    return NextResponse.json(
      { error: 'Failed to get chat response' },
      { status: 500 }
    );
  }
} 