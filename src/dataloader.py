from torch.utils.data import DataLoader
from torchvision import transforms
from src.dataset import S3VTONDataset

def get_dataloader(
    jsonl_paths,
    batch_size=4,
    resolution=1024,
    num_workers=16,
    shuffle=True
):
    """
    Creates a PyTorch DataLoader for the VTON dataset on S3.
    
    Args:
        jsonl_paths (list): List of s3:// URIs to the JSONL files.
        batch_size (int): Batch size.
        resolution (int): Image resolution (square).
        num_workers (int): Number of worker processes.
        shuffle (bool): Whether to shuffle the dataset.
    
    Returns:
        DataLoader: PyTorch DataLoader yielding dicts of tensors.
    """
    
    # Standard VTON Transforms
    # Resize -> CenterCrop (optional) -> ToTensor -> Normalize
    transform = transforms.Compose([
        transforms.Resize((resolution, resolution), interpolation=transforms.InterpolationMode.BILINEAR),
        transforms.ToTensor(),
        transforms.Normalize([0.5], [0.5]) # Normalize to [-1, 1] usually preferred for diffusion
    ])
    
    dataset = S3VTONDataset(
        jsonl_paths=jsonl_paths,
        transform=transform
    )
    
    dataloader = DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=num_workers,
        pin_memory=True
    )
    
    return dataloader

if __name__ == "__main__":
    # Test Block
    print("Testing DataLoader setup...")
    # NOTE: This requires actual S3 creds and paths to work
    pass
