import { useQuery } from '@tanstack/react-query';

export function useThesisTimeline(urn: string) {
    return useQuery({
        queryKey: ['intelligence', 'theses', urn, 'timeline'],
        queryFn: async () => {
            const res = await fetch(`/api/intelligence/theses/${urn}/timeline`);
            if (!res.ok) throw new Error('Network response was not ok');
            return res.json();
        }
    });
}

export function useConfidenceHistory(urn: string) {
    return useQuery({
        queryKey: ['intelligence', 'theses', urn, 'confidence'],
        queryFn: async () => {
            const res = await fetch(`/api/intelligence/theses/${urn}/confidence`);
            if (!res.ok) throw new Error('Network response was not ok');
            return res.json();
        }
    });
}

export function useAssumptionIntelligence(urn: string) {
    return useQuery({
        queryKey: ['intelligence', 'theses', urn, 'assumptions'],
        queryFn: async () => {
            const res = await fetch(`/api/intelligence/theses/${urn}/assumptions`);
            if (!res.ok) throw new Error('Network response was not ok');
            return res.json();
        }
    });
}

export function useThesisHealth(urn: string) {
    return useQuery({
        queryKey: ['intelligence', 'theses', urn, 'health'],
        queryFn: async () => {
            const res = await fetch(`/api/intelligence/theses/${urn}/health`);
            if (!res.ok) throw new Error('Network response was not ok');
            return res.json();
        }
    });
}
