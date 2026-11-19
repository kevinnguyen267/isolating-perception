(define (problem blocksworld)
	(:domain blocksworld)
	(:objects
		blue - block
		green - block
		orange - block
		purple - block
		red - block
		yellow - block
		robot - robot
	)
	(:init (handempty robot)
		(ontable blue)
		(clear blue)
		(ontable yellow)
		(on orange yellow)
		(clear orange)

		(ontable red)
		(on green red)
		(on purple green)
		(clear purple)
	)
	(:goal (and (handempty robot)
		(ontable purple)
		(clear purple)
		(ontable blue)
		(on red blue)
		(clear red)

		(ontable orange)
		(on yellow orange)
		(on green yellow)
		(clear green)
	))
)