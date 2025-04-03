// 채팅 API 관련 타입 정의
export interface ChatRequest {
  query: string;
}

// 백엔드 응답 인터페이스 정의
export interface SimpleDialogueResponse {
  type: 'simple_dialogue';
  message: string;
  status: string;
  highlights?: string[];
}

export interface SimulationResponse {
  type: 'simulation';
  simulations: Array<{
    id: number;
    situation: string;
    user: string;
    agent: string;
  }>;
  status: string;
  message: string;
  highlights?: string[];
}

export interface CaseResponse {
  type: 'cases';
  message: string;
  status: string;
  disputes: Array<{
    title: string;
    summary: string;
    'key points': string;
    'judge result': string;
  }>;
  highlights?: string[];
}

export interface HighlightedClauseResponse {
  type: 'highlighted_clause';
  message: string;
  highlights: string[];
  status?: string;
}

export interface HighlightsResponse {
  type: 'highlights';
  rationale: string;
  highlights: string[];
  status?: string;
}

export type BackendResponse = SimpleDialogueResponse | SimulationResponse | CaseResponse | HighlightedClauseResponse | HighlightsResponse;

// 에러 응답 인터페이스
export interface ErrorResponse {
  error: string;
} 