import { useEffect } from 'react';

type SeoProps = {
  title?: string;
  description?: string;
  image?: string;
};

export function useSeo({ title, description, image }: SeoProps) {
  useEffect(() => {
    if (title) document.title = title;
    const setMeta = (name: string, content: string) => {
      if (!content) return;
      let el = document.querySelector(`meta[name='${name}']`) as HTMLMetaElement | null;
      if (!el) {
        el = document.createElement('meta');
        el.setAttribute('name', name);
        document.head.appendChild(el);
      }
      el.setAttribute('content', content);
    };
    const setProp = (property: string, content: string) => {
      if (!content) return;
      let el = document.querySelector(`meta[property='${property}']`) as HTMLMetaElement | null;
      if (!el) {
        el = document.createElement('meta');
        el.setAttribute('property', property);
        document.head.appendChild(el);
      }
      el.setAttribute('content', content);
    };

    if (description) {
      setMeta('description', description);
      setProp('og:description', description);
      setProp('twitter:description', description);
    }
    if (title) {
      setProp('og:title', title);
      setProp('twitter:title', title);
    }
    if (image) {
      setProp('og:image', image);
      setProp('twitter:image', image);
      setMeta('twitter:card', 'summary_large_image');
    }
  }, [title, description, image]);
}