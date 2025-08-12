(
    args = { paths }
) => {
    const { paths } = args;

    function highlightElement(element, index, parentIframe = null) {
        //Create or get highlight container
        let container = document.getElementById('browser-user-highlight-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'browser-user-highlight-container';
            container.style.position = 'absolute';
            container.style.pointerEvents = 'none';
            container.style.top = '0';
            container.style.left = '0';
            container.style.width = '100%';
            container.style.height = '100%';
            container.style.zIndex = '2147483647'; // Maximum z-index value
            document.body.appendChild(container);        
        }

        // Generate a color based on the index
        const colors = [
            '#FF0000', '#00FF00', '#0000FF', '#FFA500',
            '#800080', '#008080', '#FF69B4', '#4B0082',
            '#FF4500', '#2E8B57', '#DC143C', '#4682B4'
        ];
        const colorIndex = index % colors.length;
        const baseColor = colors[colorIndex];
        const backgroundColor = `${baseColor}1A`; // 10% opacity version of the color

        // Create highlight overlay
        const overlay = document.createElement('div');
        overlay.style.position = 'absolute';
        overlay.style.border = `2px solid ${baseColor}`;
        overlay.style.backgroundColor = backgroundColor;
        overlay.style.pointerEvents = 'none';
        overlay.style.boxSizing = 'border-box';

        // Position overlay based on element, including scroll position
        const rect = element.getBoundingClientRect();
        let top = rect.top + window.scrollY;
        let left = rect.left + window.scrollX;

        // Adjust position if element is inside an iframe
        if (parentIframe) {
            const iframeRect = parentIframe.getBoundingClientRect();
            top += iframeRect.top;
            left += iframeRect.left;
        }

        overlay.style.top = `${top}px`;
        overlay.style.left = `${left}px`;
        overlay.style.width = `${rect.width}px`;
        overlay.style.height = `${rect.height}px`;

        // Create label
        const label = document.createElement('div');
        label.className = 'browser-user-highlight-label';
        label.style.position = 'absolute';
        label.style.background = baseColor;
        label.style.color = 'white';
        label.style.padding = '1px 4px';
        label.style.borderRadius = '4px';
        label.style.fontSize = `${Math.min(12, Math.max(8, rect.height / 2))}px`; // Responsive font size
        label.textContent = index;

        // Calculate label position
        const labelWidth = 20; // Approximate width
        const labelHeight = 16; // Approximate height

        // Default position (top-right corner inside the box)
        let labelTop = top + 2;
        let labelLeft = left + rect.width - labelWidth - 2;

        // Adjust if box is too small
        if (rect.width < labelWidth + 4 || rect.height < labelHeight + 4) {
            // Position outside the box if it's too small
            labelTop = top - labelHeight - 2;
            labelLeft = left + rect.width - labelWidth;
        }


        label.style.top = `${labelTop}px`;
        label.style.left = `${labelLeft}px`;

        // Add to container
        container.appendChild(overlay);
        container.appendChild(label);
    }

    const elements = []
    for (const path of paths) {
        const xPath = path.path
        const index = path.index
        
        const result = document.evaluate(
            xPath,                  
            document,               
            null,                   
            XPathResult.FIRST_ORDERED_NODE_TYPE,
            null
        );
        const element = result.singleNodeValue;
        if (!!element) elements.push({
            element,
            index
        })
    }

    for (const element of elements) {
        highlightElement(element.element, element.index)
    }
}